# Use an official Node.js runtime as a parent image
FROM node:lts AS development

ENV CI=true
ENV PORT=3000

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the entire project to the working directory
COPY . .

# Build your React app
# RUN npm run build

# Set environment variables
# ENV PORT=80
# ENV HOST=0.0.0.0

# Expose the port your app runs on
# EXPOSE 5173

# Command to run your app
CMD ["npm", "run", "dev"]