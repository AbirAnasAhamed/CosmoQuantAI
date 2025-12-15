# Python Image
FROM python:3.12-slim
# Set working directory
WORKDIR /app

# Install dependencies
# ✅ 1. Install Dependencies & Fonts (Fanatix Fix)
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    fonts-liberation \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# ✅ 2. Fix Cache Directories (Fontconfig & Matplotlib Error Fix)
# ক্যাশ ফোল্ডার তৈরি করে পারমিশন দেওয়া হচ্ছে যাতে 'worker' ইউজার লিখতে পারে
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/.matplotlib

RUN mkdir -p /tmp/.cache && chmod 777 /tmp/.cache \
    && mkdir -p /tmp/.matplotlib && chmod 777 /tmp/.matplotlib

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Fix line endings for prestart.sh (Windows compatibility)
RUN sed -i 's/\r$//' /app/prestart.sh

# Expose port
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]