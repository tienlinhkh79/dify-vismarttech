# Vismarttech Landing Design System (UI/UX Pro Max Style)

## Pattern

- Primary Pattern: Conversion-Optimized + Social Proof
- Page Order: Hero -> Core Features -> Trust/Testimonial -> Plans -> Final CTA
- CTA Placement: Above the fold, section end, final block

## Style

- Style Family: Minimal & Direct with Enterprise Blue Accent
- Visual Mood: Reliable, technical, operation-ready, B2B
- Interaction: subtle hover/focus transitions (150-250ms), no excessive motion

## Color Tokens

- Primary: `#0B57F0`
- Background: `#F8FAFF`
- Surface: `#FFFFFF`
- Border: `#D5DEF5`
- Text Primary: `#0B1220`
- Text Secondary: `#4F5B71`

## Typography

- Base Font: Inter, system-ui, sans-serif
- Heading: 700 weight, tight tracking
- Body: 400-500 weight, readable line-height

## Component Rules

- Buttons: pill radius, visible focus ring, pointer cursor
- Cards: rounded 16px, light border, clear hierarchy
- Navigation: concise labels, no over-crowding
- Testimonials: short quotes, role-based attribution

## Accessibility Checklist

- Keyboard focus visible for all interactive elements
- Contrast target: WCAG AA minimum (4.5:1 for normal text)
- Respect `prefers-reduced-motion`
- Responsive checkpoints: 375, 768, 1024, 1440

## Brand Checklist

- Company name must be `Vismarttech`
- Do not use `Dify` text on landing
- CTA links use `NEXT_PUBLIC_DIFY_APP_URL`
- Replace email contacts in `content/site.ts` before production
