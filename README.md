<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<br />
<div align="center">
  <a href="https://github.com/RehmanMuaz/JobHub-API">
    <img src="docs/logo-bg.png" alt="Roadmap" width="20%">
  </a>

  <h3 align="center">JobHub-API</h3>

  <p align="center">
    Backend API for JobHub — a platform to help users track and manage job applications efficiently.
    <br />
    <a href="https://github.com/RehmanMuaz/JobHub-API"><strong>Explore the docs »</strong></a>
    <br /><br />
    <a href="https://github.com/RehmanMuaz/JobHub-API/issues">Report Bug</a> ·
    <a href="https://github.com/RehmanMuaz/JobHub-API/issues">Request Feature</a>
  </p>
</div>

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [About the Project](#about-the-project)
  - [Built With](#built-with)
- [System Architecture](#system-architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Scraper Worker (manual run)](#scraper-worker-manual-run)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Related Projects](#related-projects)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---

## About the Project

**JobHub-API** is the backend service powering the JobHub platform. It:

- Collects, stores, and manages job postings from different sources
- Tracks application progress
- (Future) Analyzes job description text for skill insights using LLMs

Built with FastAPI (clean architecture, Pydantic schemas, dependency injection, modular services).

**Cloud deployment:**
- Containerized via Docker; deployed to Cloud Run
- Images stored in Artifact Registry
- Postgres via Neon (set DATABASE_URL)
- Redis/RQ queue via Upstash (set REDIS_URL); worker runs as a separate Cloud Run service/job
- CI/CD via GitHub Actions builds/pushes/deploys on branch pushes or manual runs


<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

### Built With

- [![Python][Python-shield]][Python-url]
- [![FastAPI][FastAPI-shield]][FastAPI-url]
- [![PostgreSQL][Postgres-shield]][Postgres-url]
- [![Docker][Docker-shield]][Docker-url]
- [![Pydantic][Pydantic-shield]][Pydantic-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## System Architecture

```mermaid
flowchart TD
    A[Frontend - React] -->|REST / GraphQL| B["JobHub-API (Google Cloud)"]
    B --> C[("PostgreSQL DB (Neon)")]
    B --> D[SentinelAuth Microservice]
    D --> E[(Auth Database)]
    B --> F[Scraper API]
    F --> G[("Redis Queue (Upstash)")]
    G --> H[Scrape Workers]

        subgraph Core Services
        B
        D
        end
```

<p align="center">
  <em>Microservice-oriented architecture enabling modular scaling and independent deployments.</em>
</p>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Getting Started

Follow these steps to run the API locally.

### Prerequisites

- Python 3.11+
- Git
- Docker (optional, for containerized setup)

Install Python packages:

```bash
pip install -r requirements.txt
```

### Installation

1. **Clone the repo**

   ```bash
   git clone https://github.com/RehmanMuaz/JobHub-API.git
   cd JobHub-API
   ```

2. **Set up a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # (macOS/Linux)
   .venv\Scripts\activate    # (Windows)
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:

   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/jobhub
   JWT_SECRET=your_jwt_secret
   ```

5. **Run the FastAPI server**
   ```bash
    uvicorn app.main:app --reload
   ```

Your API will be running at **http://localhost:8000**

### Run with Docker Compose

Launch the full stack (API, Redis, and scraper worker) locally:

```bash
docker compose up --build
```

This will start:

- `fastapi-service`: the REST API exposed on http://localhost:8000
- `jobhub-redis`: Redis instance used as the scraper job queue
- `jobhub-postgres`: PostgreSQL database for storing job postings and snapshots
- `scrape-worker`: background worker that processes queued scrape jobs

Hit <kbd>Ctrl+C</kbd> to stop all services.

### Scraper Worker (manual run)

If you prefer running services manually, start Redis and then launch a worker:

```bash
redis-server --port 6379
export PYTHONPATH=src  # macOS/Linux
python -m app.worker.runner
```

On Windows PowerShell use:

```powershell
redis-server --port 6379
$env:PYTHONPATH="src"
python -m app.worker.runner
```

Ensure a PostgreSQL instance is running and reachable via `DATABASE_URL` before launching the worker.

Submit scrape jobs via the API once the worker is active.

### Apply Database Migrations

Run Alembic migrations before starting the app (or whenever the schema changes):

```bash
docker compose run --rm api alembic upgrade head
```

If you're running locally without Docker, set `DATABASE_URL` and use the same command from your virtualenv.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Usage

Visit auto-generated docs:

- Swagger UI → `http://localhost:8000/docs`
- ReDoc → `http://localhost:8000/redoc`

Example API flow:

```bash
POST /api/v1/scrape/jobs
GET  /api/v1/scrape/jobs/{job_id}
GET  /api/v1/scrape/jobs/{job_id}/result
GET  /api/v1/job-postings
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Roadmap

![Roadmap](docs/roadmap.jpg)

- [x] Initial FastAPI project setup
- [x] Database + Dependency Injection
- [ ] Authentication microservice integration
- [ ] LinkedIn/Indeed scraper microservice
- [ ] Frontend dashboard (Next.js)
- [ ] AI-based job description analysis

See [open issues](https://github.com/RehmanMuaz/JobHub-API/issues) for all features & bugs.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Related Projects

- [SentinelAuth](https://github.com/RehmanMuaz/SentinelAuth) — Authentication microservice for JobHub.
- **JobHub-Frontend** _(Coming Soon)_ — Next.js web app for analytics & tracking.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contributing

Contributions make the open-source community great!  
If you have suggestions or improvements:

1. Fork the repo
2. Create your branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<a href="https://github.com/RehmanMuaz/JobHub-API/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RehmanMuaz/JobHub-API" alt="Contributors" />
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

Distributed under the **MIT License**. See `LICENSE.txt` for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contact

**Muaz Rehman**  
[LinkedIn](https://linkedin.com/in/muaz-rehman)  
[GitHub](https://github.com/RehmanMuaz)

Project Link: [https://github.com/RehmanMuaz/JobHub-API](https://github.com/RehmanMuaz/JobHub-API)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Acknowledgments

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Models](https://docs.pydantic.dev/)
- [Docker](https://www.docker.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Shields.io](https://shields.io/)
- [Contrib.rocks](https://contrib.rocks)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

[contributors-shield]: https://img.shields.io/github/contributors/RehmanMuaz/JobHub-API.svg?style=for-the-badge
[contributors-url]: https://github.com/RehmanMuaz/JobHub-API/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/RehmanMuaz/JobHub-API.svg?style=for-the-badge
[forks-url]: https://github.com/RehmanMuaz/JobHub-API/network/members
[stars-shield]: https://img.shields.io/github/stars/RehmanMuaz/JobHub-API.svg?style=for-the-badge
[stars-url]: https://github.com/RehmanMuaz/JobHub-API/stargazers
[issues-shield]: https://img.shields.io/github/issues/RehmanMuaz/JobHub-API.svg?style=for-the-badge
[issues-url]: https://github.com/RehmanMuaz/JobHub-API/issues
[license-shield]: https://img.shields.io/github/license/RehmanMuaz/JobHub-API.svg?style=for-the-badge
[license-url]: https://github.com/RehmanMuaz/JobHub-API/blob/main/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/muaz-rehman
[Python-shield]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[FastAPI-shield]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[Postgres-shield]: https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white
[Postgres-url]: https://www.postgresql.org/
[Docker-shield]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/
[Pydantic-shield]: https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white
[Pydantic-url]: https://docs.pydantic.dev/
