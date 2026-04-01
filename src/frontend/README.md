"""
Frontend configuration and setup instructions
"""

# Bill Processing System - Frontend

## Stack
- React 18.2+
- TypeScript
- Vite (build tool)
- Redux Toolkit (state management)
- Material-UI (UI components)
- React Query (data fetching)
- Axios (HTTP client)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── DocumentUpload/
│   │   ├── ExtractionResults/
│   │   ├── RuleManager/
│   │   ├── Dashboard/
│   │   ├── MismatchReview/
│   │   └── Navigation/
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── ProcessDocument.tsx
│   │   ├── RulesManager.tsx
│   │   ├── Dashboard.tsx
│   │   └── Review.tsx
│   ├── services/
│   │   ├── api.ts          # API client configuration
│   │   ├── documentService.ts
│   │   └── ruleService.ts
│   ├── store/
│   │   ├── documentSlice.ts
│   │   ├── ruleSlice.ts
│   │   └── store.ts
│   ├── types/
│   │   ├── document.ts
│   │   ├── rule.ts
│   │   └── api.ts
│   ├── hooks/
│   │   ├── useDocuments.ts
│   │   ├── useRules.ts
│   │   └── useAuth.ts
│   ├── styles/
│   │   ├── index.css
│   │   └── theme.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
│   ├── index.html
│   └── favicon.ico
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md

## Key Components

### DocumentUpload
- File upload with drag-and-drop
- Vendor metadata entry
- Real-time validation
- Progress tracking

### ExtractionResults
- Displays extracted data
- Shows confidence scores
- Line-item visualization
- Field-level confidence indicators

### RuleManager
- Create/edit/delete rules
- Rule enable/disable toggle
- Rule effectiveness metrics
- Rule conflict detection

### Dashboard
- Processing metrics
- Success/failure rates
- Accuracy trends
- Rule effectiveness tracking

### MismatchReview
- Manual review queue
- Side-by-side comparison (extracted vs expected)
- Approval/rejection workflow
- Batch review operations

## Setup Instructions

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Run linting
npm run lint
```

## Environment Variables

Create `.env.local`:
```
VITE_API_BASE_URL=https://api.billprocessing.example.com
VITE_AUTH_TENANT_ID=your-tenant-id
VITE_AUTH_CLIENT_ID=your-client-id
VITE_AUTH_REDIRECT_URI=http://localhost:5173
```

## Docker Build

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serve with static server
FROM node:18-alpine
RUN npm install -g serve
WORKDIR /app
COPY --from=0 /app/dist ./dist

EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```
