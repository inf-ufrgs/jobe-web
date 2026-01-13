# jobe-web
A web interface for the Jobe server

This is a tentative project to auto-grade students assignments in our programming courses.

## Repository Structure
- kubernetes: stores files necessary to deploy the components into a Kubernetes cluster
- scripts: store scripts for testing and automating some tasks
- grader: web ui for students and professors to interact with in grading assignments

## Deployment considerations
The web interface is designed to work with a Jobe server instance. You need to have a running Jobe server and configure the web interface to connect to it. In this repository, you can find a sample configuration file at the `kubernetes` folder.

The web application requires read access to the GitHub repositories where the assignments are stored. You can provide this access by creating a GitHub personal access token and configuring it in the web application. Once you have the PAT token created you can create a Secret in Kubernetes to store it securely with the following command:

```bash
kubectl create secret generic git-creds --from-literal=token=<your_personal_access_token> --namespace=<your_namespace>
```