# FindIT: Dashboard Design Specification
## Blue Color Palette + shadcn/ui + GSAP

**Project:** FindIT (Electricity Demand Forecasting Dashboard)  
**Framework:** Next.js + shadcn/ui + GSAP  
**Design Language:** Technical Dark Mode (Blue-focused)  
**Focus:** Single Dashboard Page  
**Date:** 2026-05-07

---

## 1. Design System Foundations

### 1.1 Color Palette (Blue-focused)

```javascript
// tailwind.config.ts
export const colors = {
  // Backgrounds
  'dark-bg': '#0B1120',      // Deep navy - main app background
  'card-bg': '#1F2937',      // Slate - card/panel background
  'card-border': '#374151',  // Subtle borders
  
  // Text
  'text-primary': '#F9FAFB',    // Off-white - headings
  'text-secondary': '#D1D5DB',  // Light gray - labels
  'text-muted': '#9CA3AF',      // Muted text
  
  // Accents - BLUE Color System
  'accent-blue': '#3B82F6',     // Primary blue - main metrics, focus color
  'accent-blue-light': '#60A5FA', // Light blue - hover states
  'accent-blue-dark': '#1E40AF',  // Dark blue - active states
  
  // Status Colors
  'success': '#10B981',    // Green - positive trends
  'warning': '#F59E0B',    // Orange - warnings
  'error': '#EF4444',      // Red - errors, critical
  'info': '#3B82F6',       // Blue - information
};

export const theme = {
  extend: {
    colors: colors,
    backgroundColor: {
      'dark': colors['dark-bg'],
      'card': colors['card-bg'],
    },
    borderColor: {
      'subtle': colors['card-border'],
    },
  },
};
```

### 1.2 Typography System

**Font Family:** **Geist** (via Vercel) or **Inter**

```css
/* globals.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html {
  --font-geist: 'Geist', 'Inter', sans-serif;
  font-family: var(--font-geist);
  -webkit-font-smoothing: antialiased;
}
```

**Type Scale:**

| Usage | Size | Weight | Line Height |
|-------|------|--------|-------------|
| H1 (Hero) | 80px | 700 | 1 |
| H2 (Section) | 32px | 600 | 1.2 |
| H3 (Card Title) | 18px | 600 | 1.4 |
| Body | 14px | 400 | 1.6 |
| Label | 12px | 500 | 1.5 |
| Data (Monospaced) | 14–24px | 600 | 1 |

### 1.3 Layout System

**Dashboard Layout Grid:**
```
┌─────────────────────────────────────────┐
│  Logo  │  Dashboard  │  Settings        │  ← Header (64px)
├──────────────────────────────────────────┤
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Tomorrow's Peak │ 7-Day Avg │ Health│  ← Hero Metrics (3 cards)
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │                                  │   │
│  │  48-Hour Forecast Chart          │   │ ← Main Chart (400px)
│  │                                  │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ Anomalies    │  │ Quick Stats  │    │ ← Footer Cards
│  └──────────────┘  └──────────────┘    │
│                                          │
└──────────────────────────────────────────┘

Spacing:
- Header: 64px fixed
- Main padding: 24px
- Card gaps: 16px
- Chart height: 400px
- Mobile: responsive, single column
```

### 1.4 Shadows & Effects

```css
.glass-card {
  background: rgba(31, 41, 55, 0.5);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(55, 65, 81, 0.5);
}

.shadow-sm { box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); }
.shadow-md { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
.shadow-lg { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); }

/* Blue glow effect */
.glow-blue {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
}
```

---

## 2. Component Library

### 2.1 Button Component

```typescript
// components/ui/button.tsx
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  ...props
}) => {
  const variants = {
    primary: 'bg-accent-blue text-white hover:bg-accent-blue-light active:bg-accent-blue-dark shadow-md',
    secondary: 'bg-card-bg border border-card-border text-text-primary hover:border-accent-blue',
    danger: 'bg-error text-white hover:opacity-90',
    ghost: 'text-text-primary hover:bg-card-bg',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm font-medium',
    lg: 'px-6 py-3 text-base font-semibold',
  };

  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        rounded-lg transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${sizes[size]}
      `}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
      {icon && <span>{icon}</span>}
      {props.children}
    </button>
  );
};
```

### 2.2 MetricCard Component (Hero Cards)

```typescript
// components/MetricCard.tsx
export interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  trend?: { value: number; direction: 'up' | 'down' };
  size?: 'sm' | 'md' | 'lg';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  trend,
  size = 'md',
}) => {
  const sizeStyles = {
    sm: { valueSize: '48px', labelSize: 'text-sm' },
    md: { valueSize: '64px', labelSize: 'text-base' },
    lg: { valueSize: '80px', labelSize: 'text-lg' },
  };

  return (
    <div className="glass-card rounded-xl p-6 border border-card-border">
      <div className={`text-text-secondary ${sizeStyles[size].labelSize} mb-2`}>
        {label}
      </div>
      <div
        className="data-metric text-accent-blue font-semibold"
        style={{ fontSize: sizeStyles[size].valueSize }}
      >
        {value}
      </div>
      <div className="text-text-muted text-xs mt-1">{unit}</div>

      {trend && (
        <div className={`text-sm font-semibold mt-3 ${
          trend.direction === 'up' ? 'text-success' : 'text-error'
        }`}>
          {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
        </div>
      )}
    </div>
  );
};
```

### 2.3 Card Component

```typescript
// components/ui/card.tsx
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'interactive';
  padding?: 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'lg',
  children,
  ...props
}) => {
  const variants = {
    default: 'bg-card-bg border border-card-border',
    glass: 'glass-card',
    interactive: 'bg-card-bg border border-card-border cursor-pointer hover:border-accent-blue hover:shadow-md transition-all',
  };

  const paddings = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      className={`rounded-xl ${variants[variant]} ${paddings[padding]}`}
      {...props}
    >
      {children}
    </div>
  );
};
```

### 2.4 Chart Container

```typescript
// components/ChartContainer.tsx
export interface ChartContainerProps {
  title: string;
  height?: number;
  isLoading?: boolean;
  error?: string | null;
  children: React.ReactNode;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  height = 400,
  isLoading = false,
  error,
  children,
}) => {
  return (
    <Card>
      <h3 className="text-lg font-semibold text-text-primary mb-4">{title}</h3>
      
      <div style={{ height: `${height}px`, position: 'relative', width: '100%' }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-bg bg-opacity-50 rounded-lg z-10">
            <div className="animate-spin">
              <svg className="h-8 w-8 text-accent-blue" />
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-error bg-opacity-10 rounded-lg border border-error">
            <AlertTriangle className="h-8 w-8 text-error mb-2" />
            <p className="text-text-secondary text-sm">{error}</p>
          </div>
        )}

        {!isLoading && !error && children}
      </div>
    </Card>
  );
};
```

### 2.5 Stat Card (for footer)

```typescript
// components/StatCard.tsx
export interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtext?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  value,
  subtext,
}) => {
  return (
    <Card variant="interactive">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-accent-blue bg-opacity-10 rounded-lg text-accent-blue">
          {icon}
        </div>
        <div className="flex-1">
          <p className="text-text-secondary text-sm">{label}</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{value}</p>
          {subtext && <p className="text-text-muted text-xs mt-1">{subtext}</p>}
        </div>
      </div>
    </Card>
  );
};
```

---

## 3. GSAP Animation Library

### 3.1 Animation Presets

```typescript
// lib/gsap-config.ts
import gsap from 'gsap';

export const animations = {
  // Page load
  fadeIn: (element: HTMLElement) => {
    gsap.from(element, {
      opacity: 0,
      duration: 0.5,
      ease: 'power2.out',
    });
  },

  slideInUp: (element: HTMLElement) => {
    gsap.from(element, {
      y: 30,
      opacity: 0,
      duration: 0.5,
      ease: 'power2.out',
    });
  },

  // Metric cards stagger
  cardStagger: (elements: HTMLElement[]) => {
    gsap.from(elements, {
      y: 20,
      opacity: 0,
      duration: 0.4,
      stagger: 0.1,
      ease: 'power2.out',
    });
  },

  // Blue glow on metrics
  blueGlow: (element: HTMLElement) => {
    gsap.to(element, {
      boxShadow: '0 0 30px rgba(59, 130, 246, 0.5)',
      duration: 2,
      yoyo: true,
      repeat: -1,
      ease: 'sine.inOut',
    });
  },

  // Data update pulse
  dataPulse: (element: HTMLElement) => {
    gsap.to(element, {
      scale: 1.08,
      duration: 0.3,
      yoyo: true,
      repeat: 1,
      ease: 'back.out',
    });
  },

  // Chart animation
  chartDraw: (path: SVGPathElement) => {
    const length = path.getTotalLength();
    gsap.from(path, {
      strokeDasharray: length,
      strokeDashoffset: length,
      duration: 2.5,
      ease: 'power2.inOut',
    });
  },

  // Error shake
  errorShake: (element: HTMLElement) => {
    gsap.to(element, {
      x: -8,
      duration: 0.1,
      repeat: 4,
      yoyo: true,
      ease: 'power1.inOut',
    });
  },

  // Button hover glow
  buttonGlow: (button: HTMLElement) => {
    gsap.to(button, {
      boxShadow: '0 0 15px rgba(59, 130, 246, 0.6)',
      duration: 0.3,
      overwrite: 'auto',
    });
  },

  buttonGlowOut: (button: HTMLElement) => {
    gsap.to(button, {
      boxShadow: 'none',
      duration: 0.3,
    });
  },
};

// React hook
export const useGSAPAnimation = (
  animationFn: (el: HTMLElement) => void,
  deps?: any[]
) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      animationFn(ref.current);
    }
    return () => {
      gsap.killTweensOf(ref.current);
    };
  }, deps);

  return ref;
};
```

---

## 4. Dashboard Page Layout

### 4.1 Full Dashboard Component

```typescript
// app/page.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { ChartContainer } from '@/components/ChartContainer';
import { StatCard } from '@/components/StatCard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { AlertTriangle, TrendingUp, Zap, Clock } from 'lucide-react';
import { animations } from '@/lib/gsap-config';

const mockForecastData = [
  { time: '00:00', actual: 7200, predicted: 7150 },
  { time: '04:00', actual: 6800, predicted: 6900 },
  { time: '08:00', actual: 7600, predicted: 7550 },
  { time: '12:00', actual: 7900, predicted: 7850 },
  { time: '16:00', actual: 8100, predicted: 8050 },
  { time: '20:00', actual: 8300, predicted: 8250 },
  { time: '00:00', actual: 7400, predicted: 7450 },
];

export default function Dashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Animate hero cards on mount
    if (containerRef.current) {
      const heroCards = containerRef.current.querySelectorAll('.hero-card');
      animations.cardStagger(Array.from(heroCards) as HTMLElement[]);

      // Slide in chart
      const chart = containerRef.current.querySelector('.main-chart');
      if (chart) {
        animations.slideInUp(chart as HTMLElement);
      }
    }
  }, []);

  return (
    <div ref={containerRef} className="min-h-screen bg-dark-bg p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">
          Electricity Demand Forecast
        </h1>
        <p className="text-text-secondary">
          Real-time grid demand prediction for Indonesian national system
        </p>
      </div>

      {/* Hero Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="hero-card">
          <MetricCard
            label="Tomorrow's Peak Demand"
            value="7,842"
            unit="MW"
            trend={{ value: 2.1, direction: 'up' }}
            size="lg"
          />
        </div>
        <div className="hero-card">
          <MetricCard
            label="7-Day Average"
            value="7,450"
            unit="MW"
            size="md"
          />
        </div>
        <div className="hero-card">
          <MetricCard
            label="Model Accuracy"
            value="96.2%"
            unit="RMSE"
            trend={{ value: 1.2, direction: 'up' }}
            size="md"
          />
        </div>
      </div>

      {/* Main Forecast Chart */}
      <div className="main-chart mb-8">
        <ChartContainer
          title="48-Hour Demand Forecast"
          height={400}
          isLoading={isLoading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={mockForecastData}>
              <defs>
                <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="time" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#F9FAFB' }}
              />
              <Area
                type="monotone"
                dataKey="actual"
                stroke="#3B82F6"
                fillOpacity={1}
                fill="url(#colorActual)"
                name="Actual Demand"
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#60A5FA"
                strokeDasharray="5 5"
                dot={false}
                name="Predicted Demand"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>
      </div>

      {/* Bottom Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <StatCard
          icon={<AlertTriangle className="h-6 w-6" />}
          label="Active Anomalies"
          value="3"
          subtext="Last 24 hours"
        />
        <StatCard
          icon={<TrendingUp className="h-6 w-6" />}
          label="Forecast Confidence"
          value="94.8%"
          subtext="↑ +2.1% from yesterday"
        />
      </div>

      {/* Footer Action Card */}
      <Card variant="interactive" className="p-6 border-accent-blue border-opacity-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className="h-6 w-6 text-accent-blue" />
            <div>
              <h3 className="font-semibold text-text-primary">Data Last Updated</h3>
              <p className="text-sm text-text-secondary">42 minutes ago • Next update in 18 minutes</p>
            </div>
          </div>
          <Button variant="primary" size="sm">
            Refresh Now
          </Button>
        </div>
      </Card>
    </div>
  );
}
```

---

## 5. Header Component

```typescript
// components/Header.tsx
'use client';

import { Button } from '@/components/ui/button';
import { Menu, SettingsIcon, Bell } from 'lucide-react';
import { useState } from 'react';

export const Header: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-dark-bg border-b border-card-border">
      <div className="flex items-center justify-between h-16 px-6">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-blue text-white flex items-center justify-center font-bold">
            F
          </div>
          <span className="font-bold text-text-primary hidden sm:inline">FindIT</span>
        </div>

        {/* Center - Page Title */}
        <h1 className="text-lg font-semibold text-text-primary hidden md:block">
          Dashboard
        </h1>

        {/* Right - Actions */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" icon={<Bell className="h-5 w-5" />} />
          <Button variant="ghost" size="sm" icon={<SettingsIcon className="h-5 w-5" />} />
          <Button variant="ghost" size="sm" className="md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
};
```

---

## 6. Responsive Design

**Mobile (< 768px):**
```css
- Single column layout
- Hero cards stack vertically
- Chart height: 300px
- Padding: 16px
- Touch-friendly buttons (56px min height)
```

**Tablet (768px - 1024px):**
```css
- 2-column grid for hero cards
- Full chart height (400px)
- Larger padding: 24px
```

**Desktop (> 1024px):**
```css
- 3-column grid for hero cards
- Full width layout
- Max-width: 1400px center
- Padding: 32px
```

### Tailwind Responsive Classes

```typescript
// Example in components
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Cards */}
</div>

<div className="text-sm md:text-base lg:text-lg">
  {/* Responsive text */}
</div>

<div className="p-4 md:p-6 lg:p-8">
  {/* Responsive padding */}
</div>
```

---

## 7. Color Usage Guide

### Blue Accents
```typescript
// Primary actions, charts, focus states
className="text-accent-blue"
className="bg-accent-blue"
className="border-accent-blue"
className="hover:border-accent-blue"
```

### Status Colors
```typescript
// Positive trends
className="text-success"      // Green ✓

// Warnings
className="text-warning"      // Orange ⚠

// Errors
className="text-error"        // Red ✗

// Information
className="text-info"         // Blue ℹ
```

---

## 8. Implementation Checklist

### Phase 1: Setup (Day 1)
- [ ] Create Next.js project with TypeScript
- [ ] Install: tailwindcss, shadcn/ui, gsap, recharts, lucide-react
- [ ] Configure Tailwind with blue color palette
- [ ] Create base components (Button, Card, MetricCard, ChartContainer)

### Phase 2: Dashboard (Day 2)
- [ ] Build Header component
- [ ] Create Dashboard page layout
- [ ] Add MetricCard with animations
- [ ] Integrate Recharts for forecast chart
- [ ] Add StatCard components
- [ ] Setup GSAP animations

### Phase 3: Polish (Day 3)
- [ ] Responsive design testing (mobile, tablet, desktop)
- [ ] Loading states
- [ ] Error states
- [ ] Real data integration (replace mock data)
- [ ] Fine-tune animations

---

## 9. Quick Start Commands

```bash
# 1. Create Next.js project
npx create-next-app@latest findit --typescript --tailwind --eslint

# 2. Install dependencies
npm install gsap recharts lucide-react date-fns

# 3. Initialize shadcn/ui
npx shadcn-ui@latest init

# 4. Add shadcn components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card

# 5. Start dev server
npm run dev
```

---

## 10. File Structure

```
findit/
├── app/
│   ├── layout.tsx           # Main layout with Header
│   ├── page.tsx             # Dashboard page
│   └── globals.css          # Global styles
├── components/
│   ├── ui/
│   │   ├── button.tsx
│   │   └── card.tsx
│   ├── Header.tsx
│   ├── MetricCard.tsx
│   ├── ChartContainer.tsx
│   └── StatCard.tsx
├── lib/
│   └── gsap-config.ts       # Animation presets
├── public/
├── tailwind.config.ts       # Tailwind config with blue colors
└── tsconfig.json
```

---

## 11. Key Features

✅ **Dashboard-Focused**
- Single, clean dashboard page
- Real-time metric updates
- Interactive chart with forecasts

✅ **Blue Color System**
- Primary blue for focus and metrics
- Dark backgrounds for contrast
- Green/orange/red for status

✅ **Smooth Animations**
- GSAP for entrance animations
- Data update pulses
- Button hover effects
- Chart animations

✅ **Responsive**
- Mobile-first design
- Tablet-optimized
- Desktop full-featured

✅ **Production-Ready**
- TypeScript for type safety
- Accessible components
- Error handling
- Loading states

---

## 12. Customization Tips

### Change Primary Blue
```javascript
// tailwind.config.ts
'accent-blue': '#2563EB',      // Change to any blue hex
'accent-blue-light': '#3B82F6',
'accent-blue-dark': '#1D4ED8',
```

### Adjust Chart Colors
```typescript
// In ChartContainer
<Line stroke="#2563EB" />          // Change blue shade
<Area fill="url(#colorActual)" />  // Adjust gradient
```

### Modify Animation Speed
```typescript
// In gsap-config.ts
gsap.from(element, {
  duration: 0.5,    // Change: 0.3 = faster, 0.8 = slower
  ease: 'power2.out',
});
```

---

**Document Created:** 2026-05-07  
**Status:** Ready for Implementation  
**Next Step:** Run quick start commands and begin Phase 1
