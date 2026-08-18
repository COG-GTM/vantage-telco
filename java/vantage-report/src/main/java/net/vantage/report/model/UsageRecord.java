package net.vantage.report.model;

import java.util.Objects;

/** One mediated usage record: exact megabytes for an account in a period. */
public final class UsageRecord {

    private final String accountId;
    private final String deviceUuid;
    private final String period;
    private final long usageMb;

    public UsageRecord(String accountId, String deviceUuid, String period, long usageMb) {
        this.accountId = Objects.requireNonNull(accountId, "accountId");
        this.deviceUuid = Objects.requireNonNull(deviceUuid, "deviceUuid");
        this.period = Objects.requireNonNull(period, "period");
        if (usageMb < 0L) {
            throw new IllegalArgumentException("usageMb must not be negative: " + usageMb);
        }
        this.usageMb = usageMb;
    }

    public String getAccountId() {
        return accountId;
    }

    public String getDeviceUuid() {
        return deviceUuid;
    }

    public String getPeriod() {
        return period;
    }

    public long getUsageMb() {
        return usageMb;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof UsageRecord that)) {
            return false;
        }
        return usageMb == that.usageMb
                && accountId.equals(that.accountId)
                && deviceUuid.equals(that.deviceUuid)
                && period.equals(that.period);
    }

    @Override
    public int hashCode() {
        return Objects.hash(accountId, deviceUuid, period, usageMb);
    }

    @Override
    public String toString() {
        return "UsageRecord{"
                + "accountId=" + accountId
                + ", deviceUuid=" + deviceUuid
                + ", period=" + period
                + ", usageMb=" + usageMb
                + '}';
    }
}
