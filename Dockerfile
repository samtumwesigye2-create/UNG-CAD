FROM node:20-alpine
WORKDIR /app
COPY package.json server.js ./
COPY public ./public
COPY construction-takeoff ./construction-takeoff
COPY manufacturing ./manufacturing
COPY ung-cad-3d ./ung-cad-3d
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm","start"]
