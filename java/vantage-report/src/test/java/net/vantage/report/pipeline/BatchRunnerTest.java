package net.vantage.report.pipeline;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.Queue;

import org.junit.Test;

import net.vantage.report.io.CsvUsageReader;
import net.vantage.report.model.Invoice;
import net.vantage.report.model.UsageRecord;
import net.vantage.report.rating.RatingEngine;
import net.vantage.report.report.ReportRenderer;

public class BatchRunnerTest {

    private final ReportRenderer renderer = new ReportRenderer();

    @Test
    public void rendersEveryInvoiceInSubmissionOrder() {
        List<Invoice> invoices = invoices();

        try (BatchRunner runner = new BatchRunner(renderer)) {
            List<String> rendered = runner.renderAll(invoices);
            assertEquals(invoices.size(), rendered.size());
            for (int i = 0; i < invoices.size(); i++) {
                assertTrue(rendered.get(i).contains(invoices.get(i).getAccount().getAccountId()));
            }
        }
    }

    @Test
    public void separateRunnersProduceIdenticalOutput() {
        List<Invoice> invoices = invoices();

        try (BatchRunner wide = new BatchRunner(renderer);
                BatchRunner narrow = new BatchRunner(renderer)) {
            assertEquals(narrow.renderAll(invoices), wide.renderAll(invoices));
        }
    }

    @Test
    public void executesEveryTaskExactlyOnce() {
        List<Invoice> invoices = invoices();
        Map<String, Integer> counts = new ConcurrentHashMap<>();

        try (BatchRunner runner = new BatchRunner(invoice -> {
            counts.merge(invoice.getAccount().getAccountId(), 1, Integer::sum);
            return invoice.getAccount().getAccountId();
        })) {
            runner.renderAll(invoices);
        }

        assertEquals(invoices.size(), counts.size());
        for (Invoice invoice : invoices) {
            assertEquals(Integer.valueOf(1), counts.get(invoice.getAccount().getAccountId()));
        }
    }

    @Test
    public void preservesSubmissionOrderUnderReversedCompletion() {
        List<Invoice> invoices = invoices();
        Map<Invoice, Integer> indexes = new IdentityHashMap<>();
        for (int i = 0; i < invoices.size(); i++) {
            indexes.put(invoices.get(i), i);
        }

        try (BatchRunner runner = new BatchRunner(invoice -> {
            try {
                Thread.sleep((invoices.size() - indexes.get(invoice)) * 20L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new AssertionError(e);
            }
            return invoice.getAccount().getAccountId();
        })) {
            List<String> rendered = runner.renderAll(invoices);
            for (int i = 0; i < invoices.size(); i++) {
                assertEquals(invoices.get(i).getAccount().getAccountId(), rendered.get(i));
            }
        }
    }

    @Test
    public void propagatesRuntimeExceptionFromRender() {
        List<Invoice> invoices = invoices();

        try (BatchRunner runner = new BatchRunner(invoice -> {
            if (invoice == invoices.get(0)) {
                throw new IllegalArgumentException("boom");
            }
            return invoice.getAccount().getAccountId();
        })) {
            try {
                runner.renderAll(invoices);
            } catch (IllegalArgumentException e) {
                assertEquals("boom", e.getMessage());
                return;
            }
        }
        throw new AssertionError("expected IllegalArgumentException");
    }

    @Test
    public void closeShutsDownExecutor() {
        List<Invoice> invoices = invoices();
        BatchRunner runner = new BatchRunner(renderer);
        runner.close();

        assertTrue(runner.isShutdown());
        try {
            runner.renderAll(Collections.singletonList(invoices.get(0)));
        } catch (RejectedExecutionException expected) {
            return;
        }
        throw new AssertionError("expected RejectedExecutionException");
    }

    @Test
    public void rendersOnVirtualThreads() {
        List<Invoice> invoices = invoices();
        Queue<Boolean> virtualThreads = new ConcurrentLinkedQueue<>();
        Queue<String> threadNames = new ConcurrentLinkedQueue<>();

        try (BatchRunner runner = new BatchRunner(invoice -> {
            virtualThreads.add(Thread.currentThread().isVirtual());
            threadNames.add(Thread.currentThread().getName());
            return invoice.getAccount().getAccountId();
        })) {
            runner.renderAll(invoices);
        }

        assertEquals(invoices.size(), virtualThreads.size());
        assertEquals(invoices.size(), threadNames.size());
        for (Boolean virtual : virtualThreads) {
            assertTrue(virtual);
        }
        for (String name : threadNames) {
            assertTrue(name.startsWith("vantage-render-"));
        }
    }

    private static List<Invoice> invoices() {
        List<UsageRecord> usage = new CsvUsageReader().readResource("usage-sample.csv");
        return new RatingEngine(SeedAccounts.load()).buildInvoices("2026-07", usage);
    }
}
