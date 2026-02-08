# NeuroResolv Frontend 🧠✨

A premium, glassmorphic React interface for personal growth and accountability.

## 🎨 Visual Identity

- **Theme:** Dark mode with vibrant gradients (Pink, Purple, Yellow).
- **Design System:** Glassmorphism with subtle micro-animations for a premium feel.
- **Responsive:** Built with a mobile-first approach for check-ins on the go.

## 🚀 Key User Flows

- **Reality-Check Onboarding:** Interactive negotiation with AI to set sustainable goals.
- **Dynamic Dashboard:** A central hub for managing multiple resolutions, streaks, and shields.
- **Multi-Modal Check-in:** Seamless interface for uploading video/audio or writing reflections.
- **Roadmap Visualizer:** Interactive milestone tracking with AI feedback loops.

## 🛠️ Tech Stack

- **Framework:** React + Vite
- **Styling:** Vanilla CSS with custom design tokens for maximum flexibility.
- **API Client:** Axios with custom request interceptors for security.
- **State Management:** React Context API for lightweight, efficient state handling.
- **Icons:** Lucide-React for a clean, consistent icon set.

## 🔧 Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🏗️ Structure

- `/src/components`: Reusable UI components (Modals, Cards, Banners).
- `/src/pages`: Main view logic (Dashboard, Resolution, Check-in).
- `/src/utils`: API wrappers and helper functions.
- `/src/contexts`: Authentication and Global State.

## Notes

- To manually override the API key, update Line # 2 in the the `src/utils/api.js` file.
- To manually override the API base URL, update Line # 1 in the the `src/utils/api.js` file.
