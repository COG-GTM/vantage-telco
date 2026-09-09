package net.vantage.report.pipeline;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;

import net.vantage.report.model.Invoice;
import net.vantage.report.report.ReportRenderer;

/**
 * Renders a cycle's invoices with a virtual thread-per-task executor.
 *
 * <p>Each render is submitted as a task and the {@link Future}s are joined in
 * submission order so the output stays deterministic.
 */
public final class BatchRunner implements AutoCloseable {

    private static final long SHUTDOWN_TIMEOUT_SECONDS = 30L;

    private final ExecutorService executor;
    private final Function<Invoice, String> render;

    public BatchRunner(ReportRenderer renderer) {
        this(renderer::renderInvoice);
    }

    BatchRunner(Function<Invoice, String> render) {
        this.render = render;
        this.executor = Executors.newThreadPerTaskExecutor(
                Thread.ofVirtual().name("vantage-render-", 0).factory());
    }

    /** Renders every invoice, preserving input order. */
    public List<String> renderAll(List<Invoice> invoices) {
        List<Future<String>> futures = new ArrayList<>(invoices.size());
        for (Invoice invoice : invoices) {
            futures.add(executor.submit(() -> render.apply(invoice)));
        }

        List<String> rendered = new ArrayList<>(futures.size());
        for (Future<String> future : futures) {
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
            if (cause instanceof RuntimeException) {
                throw (RuntimeException) cause;
            }
            if (cause instanceof Error) {
                throw (Error) cause;
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

    public boolean isShutdown() {
        return executor.isShutdown();
    }
}
