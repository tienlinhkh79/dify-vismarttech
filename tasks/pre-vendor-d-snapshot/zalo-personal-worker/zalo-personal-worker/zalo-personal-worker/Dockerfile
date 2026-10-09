FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
ENV PORT=3920
EXPOSE 3920
CMD ["npm", "start"]
