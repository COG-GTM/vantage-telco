package net.vantage.report.io;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import net.vantage.report.model.UsageRecord;

/**
 * Reads mediated usage from the CSV export produced by the mediation job.
 *
 * <p>Header: {@code account_id,device_uuid,period,usage_mb}.
 */
public final class CsvUsageReader {

    private static final String HEADER = "account_id,device_uuid,period,usage_mb";

    public List<UsageRecord> readFile(Path path) {
        try (InputStream in = Files.newInputStream(path)) {
            return read(in);
        } catch (IOException e) {
            throw new UncheckedIOException("failed reading usage csv: " + path, e);
        }
    }

    public List<UsageRecord> readResource(String resourceName) {
        InputStream resource = getClass().getClassLoader().getResourceAsStream(resourceName);
        if (resource == null) {
            throw new IllegalArgumentException("resource not found: " + resourceName);
        }
        try (InputStream in = resource) {
            return read(in);
        } catch (IOException e) {
            throw new UncheckedIOException("failed reading usage csv resource: " + resourceName, e);
        }
    }

    public List<UsageRecord> read(InputStream in) {
        List<UsageRecord> records = new ArrayList<>();
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        try {
            String header = reader.readLine();
            if (header == null) {
                return records;
            }
            if (!HEADER.equals(header.trim())) {
                throw new IllegalArgumentException("unexpected usage csv header: " + header);
            }
            String line;
            int lineNumber = 1;
            while ((line = reader.readLine()) != null) {
                lineNumber++;
                if (line.trim().isEmpty()) {
                    continue;
                }
                records.add(parseLine(line, lineNumber));
            }
        } catch (IOException e) {
            throw new UncheckedIOException("failed reading usage csv", e);
        }
        return records;
    }

    private UsageRecord parseLine(String line, int lineNumber) {
        String[] fields = line.split(",", -1);
        if (fields.length != 4) {
            throw new IllegalArgumentException(
                    "expected 4 fields on line " + lineNumber + ", got " + fields.length);
        }
        long usageMb;
        try {
            usageMb = Long.parseLong(fields[3].trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("bad usage_mb on line " + lineNumber + ": " + fields[3], e);
        }
        return new UsageRecord(fields[0].trim(), fields[1].trim(), fields[2].trim(), usageMb);
    }
}
