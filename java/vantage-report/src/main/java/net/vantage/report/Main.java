package net.vantage.report;

import java.nio.file.Path;
import java.util.List;

import net.vantage.report.io.CsvUsageReader;
import net.vantage.report.model.Invoice;
import net.vantage.report.model.UsageRecord;
import net.vantage.report.pipeline.BatchRunner;
import net.vantage.report.pipeline.SeedAccounts;
import net.vantage.report.rating.RatingEngine;
import net.vantage.report.report.ReportRenderer;

/**
 * Entry point: renders a billing cycle to stdout.
 *
 * <pre>
 *   java -jar vantage-report.jar 2026-07 usage.csv
 * </pre>
 *
 * <p>With no CSV argument the bundled sample export is used.
 */
public final class Main {

    private static final String DEFAULT_RESOURCE = "usage-sample.csv";

    private Main() {
        throw new AssertionError("no instances");
    }

    public static void main(String[] args) {
        String period = args.length > 0 ? args[0] : "2026-07";
        CsvUsageReader reader = new CsvUsageReader();

        List<UsageRecord> usage = args.length > 1
                ? reader.readFile(Path.of(args[1]))
                : reader.readResource(DEFAULT_RESOURCE);

        RatingEngine engine = new RatingEngine(SeedAccounts.load());
        List<Invoice> invoices = engine.buildInvoices(period, usage);
        List<UsageRecord> unlinked = engine.unlinked(usage);

        ReportRenderer renderer = new ReportRenderer();
        try (BatchRunner runner = new BatchRunner(renderer)) {
            for (String rendered : runner.renderAll(invoices)) {
                System.out.println(rendered);
            }
        }

        System.out.println(renderer.renderCycleSummary(period, invoices, unlinked));
    }
}
