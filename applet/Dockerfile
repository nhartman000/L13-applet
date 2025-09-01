FROM python:3.12-slim
WORKDIR /applet
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY applet_generic.py ./
EXPOSE 9001
CMD ["uvicorn","applet_generic:app","--host","0.0.0.0","--port","9001"]
