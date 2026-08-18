package net.vantage.report.pipeline;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;

import net.vantage.report.model.Invoice;
import net.vantage.report.report.ReportRenderer;

/**
 * Renders a cycle's invoices in parallel.
 *
 * <p>Uses a bounded platform-thread pool sized off the host CPU count: each
 * render is submitted as a {@link Callable} and the {@link Future}s are joined
 * in submission order so the output stays deterministic.
 */
public final class BatchRunner implements AutoCloseable {

    private static final long SHUTDOWN_TIMEOUT_SECONDS = 30L;

    private final ExecutorService executor;
    private final ReportRenderer renderer;

    public BatchRunner(ReportRenderer renderer) {
        this(renderer, Math.max(2, Runtime.getRuntime().availableProcessors()));
    }

    public BatchRunner(ReportRenderer renderer, int poolSize) {
        this.renderer = renderer;
        ThreadFactory factory = Thread.ofPlatform()
                .name("vantage-report-", 1)
                .daemon()
                .factory();
        this.executor = Executors.newFixedThreadPool(poolSize, factory);
    }

    /** Renders every invoice, preserving input order. */
    public List<String> renderAll(List<Invoice> invoices) {
        List<Future<String>> futures = new ArrayList<>(invoices.size());
        for (Invoice invoice : invoices) {
            futures.add(executor.submit(() -> renderer.renderInvoice(invoice)));
        }

        return futures.stream().map(BatchRunner::join).toList();
    }

    private static String join(Future<String> future) {
        try {
            return future.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while rendering invoice", e);
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof RuntimeException runtime) {
                throw runtime;
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
