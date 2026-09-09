FROM maven:3.9-eclipse-temurin-21 AS build

WORKDIR /build
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src/ src/
RUN mvn -B -q package -DskipTests

FROM eclipse-temurin:21-jre

RUN useradd --system --uid 10001 vantage
WORKDIR /app
COPY --from=build /build/target/vantage-report-*.jar /app/vantage-report.jar
USER vantage
ENTRYPOINT ["java","-jar","/app/vantage-report.jar"]
CMD ["2026-07"]
