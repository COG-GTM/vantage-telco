package net.vantage.report.pipeline;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

import net.vantage.report.model.Invoice;
import net.vantage.report.report.ReportRenderer;

/**
 * Renders a cycle's invoices concurrently with virtual threads.
 *
 * <p>Each invoice is submitted to its own virtual thread, while results are
 * joined in submission order so output stays deterministic. An optional
 * concurrency bound limits the number of renders in progress.
 */
public final class BatchRunner implements AutoCloseable {

    private static final long SHUTDOWN_TIMEOUT_SECONDS = 30L;

    private final ExecutorService executor;
    private final InvoiceRenderer renderer;
    private final Semaphore permits;

    public BatchRunner(ReportRenderer renderer) {
        this(renderer::renderInvoice, 0);
    }

    public BatchRunner(ReportRenderer renderer, int maxConcurrency) {
        this(renderer::renderInvoice, maxConcurrency);
    }

    public BatchRunner(InvoiceRenderer renderer, int maxConcurrency) {
        this.renderer = renderer;
        this.permits = maxConcurrency <= 0 ? null : new Semaphore(maxConcurrency);
        this.executor = Executors.newThreadPerTaskExecutor(
                Thread.ofVirtual().name("render-", 0).factory());
    }

    /** Renders every invoice, preserving input order. */
    public List<String> renderAll(List<Invoice> invoices) {
        List<Future<String>> futures = new ArrayList<>(invoices.size());
        for (var invoice : invoices) {
            futures.add(executor.submit(() -> {
                if (permits != null) {
                    try {
                        permits.acquire();
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        throw new IllegalStateException("interrupted while waiting for render permit", e);
                    }
                }
                try {
                    return renderer.render(invoice);
                } finally {
                    if (permits != null) {
                        permits.release();
                    }
                }
            }));
        }

        List<String> rendered = new ArrayList<>(futures.size());
        for (var future : futures) {
            rendered.add(join(future));
        }
        return List.copyOf(rendered);
    }

    private static String join(Future<String> future) {
        try {
            return future.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while rendering invoice", e);
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof RuntimeException runtimeException) {
                throw runtimeException;
            }
            if (cause instanceof Error error) {
                throw error;
            }
            throw new IllegalStateException("invoice rendering failed", cause);
        }
    }

    @Override
    public void close() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(SHUTDOWN_TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
