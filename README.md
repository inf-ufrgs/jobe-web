# 🎓 UFRGS Jobe Web Grader

A modern web interface for the **Jobe** server, designed for auto-grading student assignments in programming courses. This application allows students to submit code, receive instant feedback with detailed diffs, and provides professors with tools to manage bulk submissions and check for plagiarism.

---

## 🚀 Features

- **Federated Login (SAML)**: Integrated with UFRGS Identity Provider (IdP). Students can log in using their university ID and password.
- **Instant Feedback**: Students get immediate results with side-by-side colored diffs for failed tests.
- **Auto-Sync**: Automatically pulls the latest assignments and user lists from a private GitHub repository.
- **Professor Tools**: Bulk grade submissions via direct Moodle import or ZIP files, and run built-in similarity checks (plagiarism detection).
- **Dual-Authentication**: Seamlessly supports both Matrícula-based and SAML-based logins.
- **Responsive UI**: Clean interface built with Bootstrap 5, works on mobile devices too.

---

## 🛠 Technology Stack

- **Backend**: Python 3.9+ with [FastAPI](https://fastapi.tiangolo.com/)
- **Templating**: [Jinja2](https://jinja.palletsprojects.com/)
- **Git Integration**: [GitPython](https://gitpython.readthedocs.io/)
- **Markdown**: [PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/) for math and code highlighting.
- **Containerization**: [Docker](https://www.docker.com/)
- **Orchestration**: [Kubernetes](https://kubernetes.io/)

---

## 📋 Prerequisites

- **Jobe Server**: A running instance of the [Jobe server](https://github.com/trampani/Jobe).
- **Assignments Repo**: A Git repository containing:
    - `users.yaml`: List of authorized student and professor IDs.
    - Assignment folders with `README.md` and `config.yaml` (including test cases).

---

## 💻 Local Development

1. **Clone this repository**:
   ```bash
   git clone https://github.com/inf-ufrgs/jobe-web.git
   cd jobe-web/grader
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export JOBE_URL="http://your-jobe-server/jobe/index.php/restapi/runs"
   export GIT_REPO_URL="https://github.com/your-org/your-assignments-repo.git"
   export GIT_TOKEN="your_github_pat"
   ```

   See an example repository at [inf-ufrgs/inf01040-assignments](https://github.com/inf-ufrgs/inf01040-assignments) (private repo, ask for permission).

4. **Run the application**:
   ```bash
   uvicorn app:app --reload
   ```
   The app will be available at `http://localhost:8000`.

---

## 🐳 Building with Docker

To build the image locally (from the `grader` directory, where the Dockerfile is):

```bash
docker build -t yourdockerhub/jobe-web:latest .
```

To run the container:

```bash
docker run -p 8000:8000 \
  -e JOBE_URL="http://your-jobe-server-url" \
  -e GIT_REPO_URL="https://github.com/your-repo" \
  -e GIT_TOKEN="your-token" \
  yourdockerhub/jobe-web:latest
```

---

---

## 🔐 SAML Authentication (Federated Login)

The application supports SAML 2.0 federated login, allowing users to authenticate via the **UFRGS Identity Provider (IdP)**.

### 1. Enable SAML
Set the following environment variables:
- `SAML_ENABLED="true"`
- `SAML_SP_BASE_URL="https://your-app-domain.com"` (e.g., `https://jobe-web.k8s.inf.ufrgs.br`)
- `SESSION_SECRET_KEY="your-random-secret"` (used to sign session cookies)

### 2. Generate SP Certificates
To sign requests and decrypt assertions, you need a Service Provider (SP) certificate and private key. Run the helper script:
```bash
./scripts/generate-sp-certs.sh
```
This will create `sp.crt` and `sp.key` in `grader/saml/certs/`. **Do not commit `sp.key` to Git.**

### 3. Register with the IdP
1. Start the application with `SAML_ENABLED=true`.
2. Access the metadata endpoint at `https://your-domain.com/saml/metadata`.
3. Save the XML and send it to the UFRGS IT department (CPD).

### 4. Kubernetes Secret Setup
Store your certificates and session secret in a Kubernetes Secret (see `kubernetes/saml-secrets.yaml` for a template):
```bash
# Encode your files to base64
cat grader/saml/certs/sp.crt | base64 -w 0
cat grader/saml/certs/sp.key | base64 -w 0
# Create the secret (manually edit saml-secrets.yaml then apply)
kubectl apply -f kubernetes/saml-secrets.yaml
```

---

## ☸️ Deployment (Kubernetes)

Deployment files are located in the `kubernetes/` directory.

1. **Create the GitHub credentials secret**:
   ```bash
   kubectl create secret generic git-creds --from-literal=token=<your_token> --namespace=jobe-web
   ```

2. **Apply the manifests**:
   ```bash
   kubectl apply -f kubernetes/jobe-server.yaml
   kubectl apply -f kubernetes/frontend.yaml
   ```

These manifests assume there is a namespace named `jobe-web` and you have write access to it. Also, we use the latest version of the images from Docker Hub by default. To update the app to a new version, you need to restart the `grader-web` Deployment. No information is provided here about Ingress traffic and exposing the application to outside the cluster. That depends on your Kubernetes cluster's configuration.

---

## ⚙️ Configuration (Environment Variables)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `JOBE_URL` | The REST API endpoint of your Jobe server | `http://localhost:4000/...` |
| `GIT_REPO_URL` | URL to the assignments repository | (Required) |
| `GIT_TOKEN` | GitHub Personal Access Token for private repos | (Required) |
| `SAML_ENABLED` | Enable SAML authentication flow | `false` |
| `SAML_SP_BASE_URL` | Public URL of the application (no trailing slash) | (Required for SAML) |
| `SESSION_SECRET_KEY` | Random string for session cookie signing | (Required for SAML) |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

---

## 🤝 Contributing

We welcome contributions! To contribute:

1. **Fork** the repository.
2. **Create a branch** for your feature or bug fix (`git checkout -b feature/amazing-feature`).
3. **Commit** your changes (`git commit -m 'Add amazing feature'`).
4. **Push** to the branch (`git push origin feature/amazing-feature`).
5. **Open a Pull Request**.

Please ensure your code follows the existing style and includes comments where necessary. If you are not a maintainer of this repository, please open an issue to discuss your changes before submitting a pull request.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
