# 🎓 UFRGS Jobe Web Grader

A modern web interface for the **Jobe** server, designed for auto-grading student assignments in programming courses. This application allows students to submit code, receive instant feedback with detailed diffs, and provides professors with tools to manage bulk submissions and check for plagiarism.

---

## 🚀 Features

- **Instant Feedback**: Students get immediate results with side-by-side colored diffs for failed tests.
- **Auto-Sync**: Automatically pulls the latest assignments and user lists from a private GitHub repository.
- **Professor Tools**: Bulk grade submissions via ZIP files and run built-in similarity checks (plagiarism detection).
- **Graceful Auth**: Simple login system that uses only student/professor IDs, no passwords to remember.
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

   See an example repository at [inf-ufrgs/inf01040-assignments](https://github.com/inf-ufrgs/inf01040-assignments).

4. **Run the application**:
   ```bash
   uvicorn app:app --reload
   ```
   The app will be available at `http://localhost:8000`.

---

## 🐳 Building with Docker

To build the image locally (from the `grader` directory, where the Dockerfile is):

```bash
docker build -t julianowick/jobe-web:latest .
```

To run the container:

```bash
docker run -p 8000:8000 \
  -e JOBE_URL="http://your-jobe-server-url" \
  -e GIT_REPO_URL="https://github.com/your-repo" \
  -e GIT_TOKEN="your-token" \
  julianowick/jobe-web:latest
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
