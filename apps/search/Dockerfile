FROM node:22-alpine

WORKDIR /app

COPY apps/search/package*.json ./
RUN npm ci

COPY apps/search ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
