# Runtime secrets and settings

Local development may use a `.env` file or exported environment variables.
Production deployments should load settings from a managed secret store rather
than committing plaintext credentials. The application supports the
`<NAME>_FILE` convention for mounted secrets: when `NAME_FILE` points to a
file, its contents (with trailing newlines removed) take precedence over
`NAME`. This is implemented by `app.config.setting`.

The supported settings are:

| Setting | Purpose |
| --- | --- |
| `MONGO_URI` | MongoDB connection URI |
| `MONGO_DB` | Mongo database name, default `vantage` |
| `VANTAGE_OIDC_ISSUER` | JWT issuer, default `https://idp.vantage.local/` |
| `VANTAGE_OIDC_AUDIENCE` | JWT audience, default `vantage-net` |
| `VANTAGE_OIDC_JWKS_URL` | OIDC JWKS URL |
| `VANTAGE_OIDC_AUTHORIZATION_URL` | OAuth authorization URL |
| `VANTAGE_OIDC_TOKEN_URL` | OAuth token URL |
| `VANTAGE_AUTH_DEV_SECRET` | Local-only HS256 development secret |
| `VANTAGE_AUTH_LEEWAY_SECONDS` | JWT clock-skew allowance, default `30` |
| `VANTAGE_CORS_ORIGINS` | Comma-separated allowed browser origins |
| `VANTAGE_RATE_LIMIT_PER_MINUTE` | Per-client request limit |
| `VANTAGE_TRUST_PROXY` | Whether to trust the first forwarded client IP |

Each setting can be supplied as `NAME_FILE`, for example
`MONGO_URI_FILE=/run/secrets/mongo_uri`.

## HashiCorp Vault Agent

Vault Agent can render a database URI to a file using a template:

```hcl
template {
  destination = "/run/vantage/mongo_uri"
  contents = "{{ with secret \"secret/data/vantage\" }}{{ .Data.data.mongo_uri }}{{ end }}"
}
```

Start the application with `MONGO_URI_FILE=/run/vantage/mongo_uri`. Operators
can inspect the value through Vault without putting it in shell history or a
repository:

```bash
vault kv get -field=mongo_uri secret/vantage
```

The same pattern can be used for OIDC values and other sensitive settings by
rendering one file per setting.

## AWS Secrets Manager and ECS

Store the URI and OIDC values in AWS Secrets Manager and reference them from
the ECS task definition. ECS injects the resolved values at task start:

```json
"secrets": [
  {
    "name": "MONGO_URI",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:vantage/mongo-uri"
  },
  {
    "name": "VANTAGE_OIDC_JWKS_URL",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:vantage/oidc-jwks-url"
  }
]
```

Use task execution-role permissions scoped to the referenced secrets. For a
file-mounted integration, write the values to a task volume and set the
corresponding `*_FILE` variables instead.

## Kubernetes Secrets

Create a Kubernetes Secret and expose it through `envFrom`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: vantage-runtime
type: Opaque
stringData:
  MONGO_URI: mongodb://mongo:27017
  MONGO_DB: vantage
  VANTAGE_OIDC_JWKS_URL: https://idp.example/.well-known/jwks.json
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vantage
spec:
  template:
    spec:
      containers:
        - name: app
          image: vantage-app:latest
          envFrom:
            - secretRef:
                name: vantage-runtime
```

Alternatively, mount individual Secret keys as files and set `MONGO_URI_FILE`
or another `*_FILE` variable:

```yaml
env:
  - name: MONGO_URI_FILE
    value: /var/run/vantage-secrets/mongo_uri
volumeMounts:
  - name: vantage-secrets
    mountPath: /var/run/vantage-secrets
    readOnly: true
volumes:
  - name: vantage-secrets
    secret:
      secretName: vantage-runtime
```

## SBOM

The `make sbom` target uses Syft to produce CycloneDX JSON files. Install Syft
using the official installer or package for your platform, then run:

```bash
make sbom
```

The generated `sbom-python.cdx.json` and `sbom-java.cdx.json` files are ignored
by Git. The supply-chain workflow creates and uploads equivalent artifacts.
