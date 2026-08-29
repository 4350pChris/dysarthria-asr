FROM node:24-alpine AS build

WORKDIR /app
RUN npm install -g pnpm@11.13.1

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
ARG NUXT_UMAMI_HOST
ARG NUXT_UMAMI_ID
ENV NUXT_UMAMI_HOST=$NUXT_UMAMI_HOST
ENV NUXT_UMAMI_ID=$NUXT_UMAMI_ID
RUN pnpm build

FROM node:24-alpine

WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/.output ./.output

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
