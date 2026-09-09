package net.vantage.report.pipeline;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

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
        List<UsageRecord> usage = new CsvUsageReader().readResource("usage-sample.csv");
        List<Invoice> invoices = new RatingEngine(SeedAccounts.load()).buildInvoices("2026-07", usage);

        BatchRunner runner = new BatchRunner(renderer, 4);
        try {
            List<String> rendered = runner.renderAll(invoices);
            assertEquals(invoices.size(), rendered.size());
            for (int i = 0; i < invoices.size(); i++) {
                assertTrue(rendered.get(i).contains(invoices.get(i).getAccount().getAccountId()));
            }
        } finally {
            runner.close();
        }
    }

    @Test
    public void singleThreadedPoolProducesIdenticalOutput() {
        List<UsageRecord> usage = new CsvUsageReader().readResource("usage-sample.csv");
        List<Invoice> invoices = new RatingEngine(SeedAccounts.load()).buildInvoices("2026-07", usage);

        BatchRunner wide = new BatchRunner(renderer, 8);
        BatchRunner narrow = new BatchRunner(renderer, 1);
        try {
            assertEquals(narrow.renderAll(invoices), wide.renderAll(invoices));
        } finally {
            wide.close();
            narrow.close();
        }
    }

    @Test
    public void runsEachRenderOnNamedVirtualThread() {
        List<Invoice> invoices = invoices();
        List<Boolean> virtualThreads = new CopyOnWriteArrayList<>();
        List<String> threadNames = new CopyOnWriteArrayList<>();
        InvoiceRenderer stub = invoice -> {
            virtualThreads.add(Thread.currentThread().isVirtual());
            threadNames.add(Thread.currentThread().getName());
            return invoice.getAccount().getAccountId();
        };

        try (BatchRunner runner = new BatchRunner(stub, 0)) {
            runner.renderAll(invoices);
        }

        assertEquals(invoices.size(), virtualThreads.size());
        assertEquals(invoices.size(), threadNames.size());
        for (int i = 0; i < invoices.size(); i++) {
            assertTrue(virtualThreads.get(i));
            assertTrue(threadNames.get(i).startsWith("render-"));
        }
    }

    @Test
    public void outputOrderMatchesInputRegardlessOfScheduling() {
        List<Invoice> invoices = invoices();
        ConcurrentHashMap<String, Integer> indexes = new ConcurrentHashMap<>();
        for (int i = 0; i < invoices.size(); i++) {
            indexes.put(invoices.get(i).getAccount().getAccountId(), i);
        }
        InvoiceRenderer stub = invoice -> {
            int index = indexes.get(invoice.getAccount().getAccountId());
            try {
                Thread.sleep((invoices.size() - index) % 7 * 3L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(e);
            }
            return renderer.renderInvoice(invoice);
        };
        List<String> expected = new ArrayList<>();
        for (Invoice invoice : invoices) {
            expected.add(renderer.renderInvoice(invoice));
        }

        try (BatchRunner runner = new BatchRunner(stub, 0)) {
            for (int i = 0; i < 3; i++) {
                assertEquals(expected, runner.renderAll(invoices));
            }
        }
    }

    @Test
    public void propagatesRendererExceptionAsIs() {
        List<Invoice> invoices = invoices();
        IllegalArgumentException specific = new IllegalArgumentException("specific");
        InvoiceRenderer stub = invoice -> {
            if (invoice == invoices.get(2)) {
                throw specific;
            }
            return "rendered";
        };

        try (BatchRunner runner = new BatchRunner(stub, 0)) {
            IllegalArgumentException thrown = assertThrows(
                    IllegalArgumentException.class, () -> runner.renderAll(invoices));
            assertSame(specific, thrown);
        }
    }

    @Test
    public void propagatesErrorsAsIs() {
        List<Invoice> invoices = invoices();
        InvoiceRenderer stub = invoice -> {
            throw new AssertionError("boom");
        };

        try (BatchRunner runner = new BatchRunner(stub, 0)) {
            assertThrows(AssertionError.class, () -> runner.renderAll(invoices));
        }
    }

    @Test
    public void boundedConcurrencyNeverExceedsLimit() {
        List<Invoice> invoices = invoices();
        AtomicInteger inFlight = new AtomicInteger();
        AtomicInteger peak = new AtomicInteger();
        InvoiceRenderer stub = invoice -> {
            int current = inFlight.incrementAndGet();
            peak.accumulateAndGet(current, Math::max);
            try {
                Thread.sleep(5L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(e);
            } finally {
                inFlight.decrementAndGet();
            }
            return "rendered";
        };

        try (BatchRunner runner = new BatchRunner(stub, 3)) {
            assertEquals(invoices.size(), runner.renderAll(invoices).size());
        }
        assertTrue(peak.get() <= 3);
    }

    @Test
    public void fansOutThousandsOfBlockingRenders() {
        List<Invoice> invoices = invoices();
        List<Invoice> manyInvoices = new ArrayList<>(2000);
        for (int i = 0; i < 2000; i++) {
            manyInvoices.add(invoices.get(i % invoices.size()));
        }
        InvoiceRenderer stub = invoice -> {
            try {
                Thread.sleep(20L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(e);
            }
            return "rendered";
        };
        long started = System.nanoTime();

        try (BatchRunner runner = new BatchRunner(stub, 0)) {
            assertEquals(2000, runner.renderAll(manyInvoices).size());
        }

        long elapsedMillis = (System.nanoTime() - started) / 1_000_000L;
        assertTrue("rendering took " + elapsedMillis + " ms", elapsedMillis < 5000L);
    }

    private List<Invoice> invoices() {
        List<UsageRecord> usage = new CsvUsageReader().readResource("usage-sample.csv");
        return new RatingEngine(SeedAccounts.load()).buildInvoices("2026-07", usage);
    }
}
