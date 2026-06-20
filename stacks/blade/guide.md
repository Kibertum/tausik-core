# Stack: Blade

Laravel Blade + Livewire + Tailwind CSS + SCSS — frontend stack for server-rendered apps.

## Testing
- **Blade views**: `$this->get('/url')->assertSee('text')->assertDontSee('secret')`
- **Livewire**: `Livewire::test(Component::class)->set('search', 'query')->assertSeeHtml('<div')`
- **Accessibility**: axe-core via `npm run test:a11y`, Lighthouse CI
- **Visual**: Percy or Playwright screenshots for regression

## Review Checklist
- [ ] Semantic HTML: `<article>`, `<section>`, `<nav>`, `<aside>`, `<header>`, `<main>`, `<footer>`
- [ ] One `<h1>` per page, logical heading hierarchy (h1 → h2 → h3, no skipping)
- [ ] `alt` on all `<img>` — descriptive for content, empty for decorative
- [ ] `width` and `height` attributes on `<img>` — prevents CLS
- [ ] `<label>` for every `<input>` — linked via `for`/`id`
- [ ] `<button>` for actions, `<a>` for navigation — never `<div onclick>`
- [ ] ARIA landmarks: `role="banner"`, `role="main"`, `role="contentinfo"`
- [ ] `aria-current="page"` on active nav links
- [ ] Focus styles visible: no `outline: none` without replacement
- [ ] Touch targets minimum 44×44px (WCAG 2.5.5)
- [ ] Color contrast 4.5:1 for text, 3:1 for UI elements
- [ ] No inline styles — use CSS classes or Tailwind utilities
- [ ] No HTML comments — use Blade `{{-- --}}`
- [ ] `@csrf` on every form
- [ ] `{{ }}` for escaped output, `{!! !!}` only for trusted HTML (editor content)

## Conventions
- **Layout**: `<x-layout>` component or `@extends('layouts.app')`
- **Partials**: `@include('partials.breadcrumbs')` for reusable fragments
- **Components**: `resources/views/components/` for Blade components
- **Livewire**: `app/Http/Livewire/` + `resources/views/livewire/`
- **Assets**: Vite entry points in `vite.config.js`, `@vite()` directive
- **Styles**: Tailwind utilities first, SCSS for complex components, CSS custom properties for tokens
- **Icons**: SVG sprite `<symbol>` + `<use>` — not inline SVG paths
- **Images**: `<picture>` with WebP + fallback, `loading="lazy"` below fold
- **Fonts**: woff2 only, `font-display: swap`, preload critical fonts
- **Schema.org**: JSON-LD in `<script type="application/ld+json">` — not microdata

## Common Pitfalls
- **Livewire + Alpine**: Alpine `x-data` resets on Livewire re-render — use `wire:ignore` or `@entangle`
- **Blade caching**: `php artisan view:clear` after template changes in production
- **CSRF on AJAX**: include `@csrf` token in headers for Livewire/fetch requests
- **@push/@stack order**: `@push('scripts')` appends, `@prepend` for dependencies
- **Tailwind purge**: ensure `content` in `tailwind.config.js` includes all Blade/Livewire paths
- **No-JS fallback**: `<noscript>` blocks, CSS `:target` pseudo-class, `<details>/<summary>`
- **CLS from lazy images**: always set `width`/`height` or use `aspect-ratio` CSS
- **Mixed content**: `asset()` respects `APP_URL` — ensure HTTPS in production
