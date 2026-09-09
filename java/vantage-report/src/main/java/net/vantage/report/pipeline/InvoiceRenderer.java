package net.vantage.report.pipeline;

import net.vantage.report.model.Invoice;

@FunctionalInterface
public interface InvoiceRenderer {

    String render(Invoice invoice);
}
