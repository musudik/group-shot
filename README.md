# GroupShot — Team Photo Creator

A stylish, mobile-responsive web app that lets you create beautiful group photos from individual team member images.

## Features

- 📸 **Drag & drop** image uploads (up to 30 team members)
- 🖼 **12 aspect ratios**: 16:9, 9:16, 4:5, 5:4, 1:1, 3:2, 2:3, 4:3, 3:4, 21:9, 2:1, 1:2
- ✂️ **7 photo shapes**: Circle, Square, Rounded, Heart, Hexagon, Diamond, Star
- 📐 **3 layout modes**: Auto Grid, Single Row, Pyramid
- 🎨 **5 background themes**: Dark, Forest, Red, Light, Gradient
- 🔤 **Title & Subtitle** (optional, rendered in Bebas Neue / Oswald fonts)
- ⬇️ **High-res PNG export** (1080p+)
- 📱 **Mobile responsive** design

## Design Theme

Inspired by vintage sports poster aesthetics:
- **Colors**: Dark green `#1B3A2D`, Deep red `#C0392B`, Cream `#F0EAD6`
- **Fonts**: Bebas Neue (display), Oswald (body), Inter (UI)

## Deploy to Vercel

1. Push this folder to a GitHub repository
2. Go to [vercel.com](https://vercel.com) → New Project
3. Import your repo
4. Click **Deploy** — no build step needed!

## Local Development

Just open `index.html` in any browser — no server required.

```bash
# Or use a simple HTTP server
python3 -m http.server 3000
# Then open http://localhost:3000
```

## Project Structure

```
group-photo-creator/
├── index.html      ← Full single-file app
├── vercel.json     ← Vercel routing config
└── README.md       ← This file
```
