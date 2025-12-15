FROM python:3.12-slim
WORKDIR /app

# ✅ ফন্ট এবং WeasyPrint এর ডিপেন্ডেন্সি
RUN apt-get update && apt-get install -y \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info libpangoft2-1.0-0 libharfbuzz-subset0 \
    libjpeg-dev libopenjp2-7-dev fonts-liberation fontconfig \
    && rm -rf /var/lib/apt/lists/*

# ✅ ফন্ট ক্যাশ এবং কনফিগ ডিরেক্টরি পারমিশন
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/.matplotlib
RUN mkdir -p /tmp/.cache /tmp/.matplotlib && chmod -R 777 /tmp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN sed -i 's/\r$//' /app/prestart.sh
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]