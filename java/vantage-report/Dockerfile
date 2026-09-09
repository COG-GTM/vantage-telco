# syntax=docker/dockerfile:1

# Base images can be redirected to a registry mirror (e.g. public.ecr.aws/docker/library/...).
ARG MAVEN_IMAGE=maven:3-eclipse-temurin-21
ARG JRE_IMAGE=eclipse-temurin:21-jre-alpine

# Optional local Maven repository seed. Empty by default (dependencies come from Maven Central);
# override with `docker build --build-context m2seed=$HOME/.m2 ...` to build from a warm cache.
FROM scratch AS m2seed

FROM ${MAVEN_IMAGE} AS build

WORKDIR /build
COPY pom.xml ./
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    --mount=type=bind,from=m2seed,target=/m2seed \
    MVN_FLAGS=""; \
    if [ -d /m2seed/repository ]; then mkdir -p /root/.m2/repository && cp -a /m2seed/repository/. /root/.m2/repository/ && MVN_FLAGS="-o -Daether.enhancedLocalRepository.split=false -Daether.enhancedLocalRepository.trackingFilename=_none_"; fi \
    && mvn -B -q $MVN_FLAGS -DskipTests package


FROM ${JRE_IMAGE} AS runtime

RUN apk upgrade --no-cache \
    && addgroup -S -g 10001 vantage \
    && adduser -S -u 10001 -G vantage -h /srv/vantage -H vantage \
    && mkdir -p /out \
    && chown vantage:vantage /out

WORKDIR /srv/vantage
COPY --from=build /build/target/vantage-report-*.jar ./vantage-report.jar
COPY --chown=vantage:vantage --chmod=0755 docker-entrypoint.sh ./docker-entrypoint.sh

USER vantage
VOLUME ["/out"]
ENV OUTPUT_DIR=/out

# Same positional arguments as `mvn exec:java -Dexec.args="<period> [usage.csv]"`.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["2026-07"]
