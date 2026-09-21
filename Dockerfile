FROM python:3.12-alpine
WORKDIR /app
# Solo libreria standard, nessuna dipendenza da installare
COPY app.py index.html services.json ./
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/api/health || exit 1
CMD ["python", "-u", "app.py"]
