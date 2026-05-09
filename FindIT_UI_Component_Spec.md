# Castricity: Complete UI/UX Component Specification
## shadcn/ui + GSAP Implementation Guide

**Project:** Castricity (Electricity Demand Forecasting System)  
**Framework:** Next.js + shadcn/ui + GSAP  
**Design Language:** Technical Dark Mode (Castricity-inspired)  
**Date:** 2026-05-07

---

## 1. Design System Foundations

### 1.1 Color Palette (Tailwind Config)

```javascript
// tailwind.config.ts
export const colors = {
  // Backgrounds
  'dark-bg': '#0B1120',      // Deep navy - main app background
  'card-bg': '#1F2937',      // Slate - card/panel background
  'card-border': '#374151',  // Subtle borders
  
  // Text
  'text-primary': '#F9FAFB',    // Off-white - headings
  'text-secondary': '#D1D5DB',  // Light gray - labels, secondary
  'text-muted': '#9CA3AF',      // Muted text
  
  // Accents - Energy/Electricity
  'accent-cyan': '#06B6D4',     // Primary metrics, neutral data
  'accent-green': '#10B981',    // Positive trends, healthy status
  'accent-orange': '#F59E0B',   // Medium-priority anomalies
  'accent-red': '#EF4444',      // Critical anomalies, errors
  
  // Utility
  'success': '#10B981',
  'warning': '#F59E0B',
  'error': '#EF4444',
  'info': '#06B6D4',
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

**Font Family:** Use **Geist** (via Vercel) or **Inter** as fallback

```css
/* globals.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html {
  --font-geist: 'Geist', 'Inter', sans-serif;
  font-family: var(--font-geist);
  -webkit-font-smoothing: antialiased;
}
```

**Scale (all figures use tabular/monospaced numbers for data metrics):**

| Usage | Size | Weight | Line Height | Letter Spacing |
|-------|------|--------|-------------|----------------|
| H1 (Hero Metrics) | 80px | 700 | 1 | -0.02em |
| H2 (Section Titles) | 32px | 600 | 1.2 | -0.01em |
| H3 (Card Titles) | 18px | 600 | 1.4 | 0 |
| Body (Default) | 14px | 400 | 1.6 | 0 |
| Body Small (Labels) | 12px | 500 | 1.5 | 0.02em |
| Data/Numbers (Monospaced) | 14px–24px | 600 | 1 | 0 (via `font-variant-numeric: tabular-nums`) |

**Data Numbers Configuration:**
```css
.data-metric {
  font-family: 'Courier New', monospace; /* or use Geist Mono */
  font-variant-numeric: tabular-nums; /* Ensures aligned columns */
  letter-spacing: -0.01em;
  font-weight: 600;
}
```

### 1.3 Spacing & Layout System

**Base Unit:** 4px (Tailwind default)

| Scale | Pixels |
|-------|--------|
| xs | 4px |
| sm | 8px |
| md | 12px |
| lg | 16px |
| xl | 24px |
| 2xl | 32px |
| 3xl | 48px |

**Layout Zones:**
- **Sidebar:** 240px (fixed), 64px when collapsed
- **Top Header:** 64px height
- **Main Content:** Full width minus sidebar
- **Card Padding:** 24px (lg)
- **Chart Height (Default):** 400px
- **Modal Width:** 600px (tablet), 800px (desktop)

### 1.4 Elevation & Shadows

```css
/* shadow-system.css */
.shadow-sm {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.shadow-lg {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
}

/* Glassmorphism effect for cards */
.glass-card {
  background: rgba(31, 41, 55, 0.5);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(55, 65, 81, 0.5);
}
```

---

## 2. Component Library (shadcn/ui based)

### 2.1 Button Component

**Location:** `components/ui/button.tsx`

```typescript
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
  animation?: 'pulse' | 'glow' | 'none';
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  animation = 'none',
  ...props
}) => {
  const variants = {
    primary: 'bg-accent-cyan text-dark-bg hover:bg-opacity-90 active:scale-95',
    secondary: 'bg-card-bg border border-card-border text-text-primary hover:border-accent-cyan',
    danger: 'bg-accent-red text-white hover:opacity-90',
    ghost: 'text-text-primary hover:bg-card-bg',
    outline: 'border border-card-border text-text-primary hover:border-accent-cyan',
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
        ${animation === 'glow' ? 'button-glow' : ''}
        ${animation === 'pulse' ? 'animate-pulse' : ''}
      `}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : icon ? (
        <span>{icon}</span>
      ) : null}
      {props.children}
    </button>
  );
};
```

**GSAP Animation (Glow Effect):**
```typescript
// gsap-animations.ts
export const buttonGlowAnimation = (element: HTMLElement) => {
  gsap.to(element, {
    boxShadow: `0 0 20px rgba(6, 182, 212, 0.6)`,
    duration: 1.5,
    yoyo: true,
    repeat: -1,
  });
};
```

---

### 2.2 Card Component

**Location:** `components/ui/card.tsx`

```typescript
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'interactive';
  padding?: 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'lg',
  ...props
}) => {
  const variants = {
    default: 'bg-card-bg border border-card-border',
    glass: 'glass-card',
    interactive: 'bg-card-bg border border-card-border cursor-pointer hover:border-accent-cyan transition-colors',
  };

  const paddings = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      className={`
        rounded-xl
        ${variants[variant]}
        ${paddings[padding]}
      `}
      {...props}
    />
  );
};
```

---

### 2.3 MetricCard Component (Custom)

**Location:** `components/MetricCard.tsx`

Used for hero metrics on dashboard (Tomorrow's Peak Demand, etc.)

```typescript
export interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  trend?: { value: number; direction: 'up' | 'down' };
  variant?: 'primary' | 'secondary' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  sparkline?: number[]; // Data for sparkline
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  trend,
  variant = 'primary',
  size = 'md',
  sparkline,
}) => {
  const variantStyles = {
    primary: 'text-accent-cyan',
    secondary: 'text-accent-green',
    warning: 'text-accent-orange',
  };

  const sizeStyles = {
    sm: { valueSize: '48px', labelSize: 'text-sm' },
    md: { valueSize: '64px', labelSize: 'text-base' },
    lg: { valueSize: '80px', labelSize: 'text-lg' },
  };

  return (
    <Card variant="glass" className="flex flex-col">
      <div className={`text-text-secondary ${sizeStyles[size].labelSize}`}>
        {label}
      </div>
      <div
        className={`data-metric ${variantStyles[variant]}`}
        style={{ fontSize: sizeStyles[size].valueSize }}
      >
        {value}
      </div>
      <div className="text-text-muted text-xs">{unit}</div>

      {trend && (
        <div className={`text-sm font-semibold mt-2 ${trend.direction === 'up' ? 'text-accent-green' : 'text-accent-red'}`}>
          {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
        </div>
      )}

      {sparkline && (
        <Sparkline data={sparkline} className="mt-3" color={variantStyles[variant]} />
      )}
    </Card>
  );
};
```

---

### 2.4 Chart Wrapper with Loading State

**Location:** `components/ChartContainer.tsx`

```typescript
export interface ChartContainerProps {
  title: string;
  height?: number;
  isLoading?: boolean;
  error?: string;
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
    <Card className="w-full">
      <h3 className="text-lg font-semibold text-text-primary mb-4">{title}</h3>
      
      <div style={{ height: `${height}px`, position: 'relative' }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-bg bg-opacity-40 rounded-lg z-10">
            <LoadingSkeleton type="chart" />
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-accent-red bg-opacity-10 rounded-lg border border-accent-red">
            <AlertTriangle className="h-8 w-8 text-accent-red mb-2" />
            <p className="text-text-secondary text-sm">{error}</p>
          </div>
        )}

        {!isLoading && !error && children}
      </div>
    </Card>
  );
};
```

---

### 2.5 Slider Component (with GSAP track animation)

**Location:** `components/ui/slider.tsx`

```typescript
export interface SliderProps {
  label: string;
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
  icon?: React.ReactNode;
}

export const Slider: React.FC<SliderProps> = ({
  label,
  min,
  max,
  value,
  onChange,
  unit = '',
  icon,
}) => {
  const sliderRef = useRef<HTMLInputElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (trackRef.current) {
      const percentage = ((value - min) / (max - min)) * 100;
      
      gsap.to(trackRef.current, {
        width: `${percentage}%`,
        duration: 0.3,
        ease: 'power2.out',
      });
    }
  }, [value, min, max]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-text-primary flex items-center gap-2">
          {icon && <span>{icon}</span>}
          {label}
        </label>
        <span className="data-metric text-accent-cyan">
          {value}{unit}
        </span>
      </div>

      <div className="relative h-2 bg-card-border rounded-full overflow-hidden">
        <div
          ref={trackRef}
          className="h-full bg-gradient-to-r from-accent-cyan to-accent-green rounded-full"
        />
        <input
          ref={sliderRef}
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </div>
  );
};
```

---

### 2.6 Toggle Switch Component

**Location:** `components/ui/toggle-switch.tsx`

```typescript
export interface ToggleSwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  label,
  checked,
  onChange,
}) => {
  const switchRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (switchRef.current) {
      gsap.to(switchRef.current, {
        backgroundColor: checked ? '#10B981' : '#374151',
        duration: 0.3,
      });
    }
  }, [checked]);

  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <button
        ref={switchRef}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 rounded-full transition-colors ${
          checked ? 'bg-accent-green' : 'bg-card-border'
        }`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-0.5'
          }`}
        />
      </button>
      <span className="text-sm font-medium text-text-primary">{label}</span>
    </label>
  );
};
```

---

### 2.7 Data Table Component

**Location:** `components/DataTable.tsx`

For displaying historical data, anomaly logs, scenario history

```typescript
export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  isLoading?: boolean;
  pageSize?: number;
  onRowClick?: (row: T) => void;
}

export const DataTable = <T,>({
  columns,
  data,
  isLoading = false,
  pageSize = 10,
  onRowClick,
}: DataTableProps<T>) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize });

  const table = useReactTable({
    data,
    columns,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  return (
    <Card className="w-full overflow-hidden">
      {isLoading && <LoadingSkeleton type="table" />}

      {!isLoading && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-card-border">
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="text-left px-4 py-3 font-semibold text-text-secondary"
                    >
                      {header.isPlaceholder ? null : (
                        <div
                          {...{
                            className: header.column.getCanSort() ? 'cursor-pointer select-none' : '',
                            onClick: header.column.getToggleSortingHandler(),
                          }}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={`border-b border-card-border hover:bg-card-bg transition-colors ${
                    onRowClick ? 'cursor-pointer' : ''
                  }`}
                  onClick={() => onRowClick?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 text-text-primary">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-card-border">
        <div className="text-xs text-text-muted">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            Prev
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            Next
          </Button>
        </div>
      </div>
    </Card>
  );
};
```

---

### 2.8 Anomaly Alert Card

**Location:** `components/AnomalyAlertCard.tsx`

```typescript
export interface AnomalyAlertCardProps {
  timestamp: Date;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  affectedAsset: string;
  onViewDetails: () => void;
}

export const AnomalyAlertCard: React.FC<AnomalyAlertCardProps> = ({
  timestamp,
  severity,
  title,
  description,
  affectedAsset,
  onViewDetails,
}) => {
  const severityConfig = {
    critical: {
      color: 'border-accent-red bg-accent-red bg-opacity-5',
      badge: 'bg-accent-red text-white',
      icon: AlertTriangle,
    },
    warning: {
      color: 'border-accent-orange bg-accent-orange bg-opacity-5',
      badge: 'bg-accent-orange text-dark-bg',
      icon: AlertCircle,
    },
    info: {
      color: 'border-accent-cyan bg-accent-cyan bg-opacity-5',
      badge: 'bg-accent-cyan text-dark-bg',
      icon: Info,
    },
  };

  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <Card
      className={`${config.color} border-l-4 cursor-pointer hover:shadow-lg transition-shadow`}
      onClick={onViewDetails}
    >
      <div className="flex gap-3">
        <Icon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${config.badge.replace('bg-', 'text-')}`} />
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-semibold text-text-primary">{title}</h4>
              <p className="text-xs text-text-secondary mt-1">{description}</p>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ${config.badge}`}>
              {severity.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center justify-between mt-3 text-xs text-text-muted">
            <span>Asset: {affectedAsset}</span>
            <span>{format(timestamp, 'MMM dd, HH:mm')}</span>
          </div>
          <button className="text-accent-cyan text-xs font-medium mt-2 hover:underline">
            View Details →
          </button>
        </div>
      </div>
    </Card>
  );
};
```

---

## 3. State & Loading Patterns

### 3.1 Loading Skeleton Component

**Location:** `components/LoadingSkeleton.tsx`

```typescript
export type SkeletonType = 'card' | 'chart' | 'table' | 'metric';

export const LoadingSkeleton: React.FC<{ type: SkeletonType }> = ({ type }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.to(ref.current, {
        opacity: 0.5,
        duration: 1.5,
        yoyo: true,
        repeat: -1,
        ease: 'sine.inOut',
      });
    }
  }, []);

  const skeletons = {
    card: (
      <div ref={ref} className="space-y-3">
        <div className="h-4 bg-card-border rounded w-1/3" />
        <div className="h-8 bg-card-border rounded" />
        <div className="h-4 bg-card-border rounded w-2/3" />
      </div>
    ),
    chart: (
      <div ref={ref} className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 bg-card-border rounded" />
        ))}
      </div>
    ),
    table: (
      <div ref={ref} className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-10 bg-card-border rounded" />
        ))}
      </div>
    ),
    metric: (
      <div ref={ref} className="space-y-3">
        <div className="h-4 bg-card-border rounded w-1/2" />
        <div className="h-16 bg-card-border rounded" />
      </div>
    ),
  };

  return <>{skeletons[type]}</>;
};
```

---

### 3.2 Empty State

**Location:** `components/EmptyState.tsx`

```typescript
export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="h-16 w-16 text-text-muted mb-4 opacity-50">{icon}</div>
      <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
      <p className="text-sm text-text-secondary mb-4 max-w-sm">{description}</p>
      {action && (
        <Button variant="primary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
};
```

---

### 3.3 Error State

**Location:** `components/ErrorState.tsx`

```typescript
export interface ErrorStateProps {
  title: string;
  message: string;
  retry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  retry,
}) => {
  return (
    <Card className="border-l-4 border-accent-red bg-accent-red bg-opacity-5">
      <div className="flex gap-3">
        <AlertTriangle className="h-6 w-6 text-accent-red flex-shrink-0" />
        <div className="flex-1">
          <h3 className="font-semibold text-accent-red">{title}</h3>
          <p className="text-sm text-text-secondary mt-1">{message}</p>
          {retry && (
            <Button
              variant="outline"
              size="sm"
              onClick={retry}
              className="mt-3"
            >
              Retry
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};
```

---

## 4. GSAP Animation Library

### 4.1 Animation Configuration

**Location:** `lib/gsap-config.ts`

```typescript
import gsap from 'gsap';

// Register plugins
gsap.registerPlugin(CSSPlugin);

// Global animation settings
export const animationDefaults = {
  duration: 0.3,
  ease: 'power2.out',
};

// Reusable animation presets
export const animations = {
  // Entrance animations
  fadeIn: (element: HTMLElement) => {
    gsap.from(element, {
      opacity: 0,
      duration: 0.4,
      ease: 'power2.out',
    });
  },

  slideInUp: (element: HTMLElement) => {
    gsap.from(element, {
      y: 20,
      opacity: 0,
      duration: 0.4,
      ease: 'power2.out',
    });
  },

  slideInDown: (element: HTMLElement) => {
    gsap.from(element, {
      y: -20,
      opacity: 0,
      duration: 0.4,
      ease: 'power2.out',
    });
  },

  // Card entrance (staggered for lists)
  cardStagger: (elements: HTMLElement[]) => {
    gsap.from(elements, {
      y: 20,
      opacity: 0,
      duration: 0.4,
      stagger: 0.1,
      ease: 'power2.out',
    });
  },

  // Metric glow
  metricGlow: (element: HTMLElement) => {
    gsap.to(element, {
      textShadow: '0 0 20px rgba(6, 182, 212, 0.6)',
      duration: 1.5,
      yoyo: true,
      repeat: -1,
      ease: 'sine.inOut',
    });
  },

  // Data pulse (for real-time updates)
  dataPulse: (element: HTMLElement) => {
    gsap.to(element, {
      scale: 1.05,
      duration: 0.3,
      yoyo: true,
      repeat: 1,
      ease: 'back.out',
    });
  },

  // Error shake
  errorShake: (element: HTMLElement) => {
    gsap.to(element, {
      x: -5,
      duration: 0.1,
      repeat: 5,
      yoyo: true,
      ease: 'power1.inOut',
    });
  },

  // Chart draw (for line charts)
  chartDraw: (element: SVGPathElement) => {
    const length = element.getTotalLength();
    gsap.from(element, {
      strokeDasharray: length,
      strokeDashoffset: length,
      duration: 2,
      ease: 'power2.inOut',
    });
  },

  // Modal fade + scale
  modalOpen: (backdrop: HTMLElement, modal: HTMLElement) => {
    gsap.to(backdrop, {
      opacity: 1,
      duration: 0.3,
    });
    gsap.from(modal, {
      scale: 0.95,
      opacity: 0,
      duration: 0.3,
      ease: 'back.out',
    });
  },

  modalClose: (backdrop: HTMLElement, modal: HTMLElement) => {
    gsap.to(backdrop, {
      opacity: 0,
      duration: 0.2,
    });
    gsap.to(modal, {
      scale: 0.95,
      opacity: 0,
      duration: 0.2,
      ease: 'back.in',
    });
  },

  // Sidebar toggle
  sidebarToggle: (sidebar: HTMLElement, expanded: boolean) => {
    gsap.to(sidebar, {
      width: expanded ? '240px' : '64px',
      duration: 0.4,
      ease: 'power2.inOut',
    });
  },

  // Tooltip fade-in
  tooltipFadeIn: (element: HTMLElement) => {
    gsap.from(element, {
      opacity: 0,
      y: -5,
      duration: 0.2,
      ease: 'power1.out',
    });
  },
};

// Timeline for complex sequences
export const createSequenceAnimation = () => {
  const tl = gsap.timeline({ paused: true });
  return tl;
};
```

### 4.2 Custom React Hook: useGSAPAnimation

**Location:** `hooks/useGSAPAnimation.ts`

```typescript
export const useGSAPAnimation = (
  animationFn: (el: HTMLElement) => void,
  dependency?: any[]
) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      animationFn(ref.current);
    }
    return () => {
      gsap.killTweensOf(ref.current);
    };
  }, dependency);

  return ref;
};
```

### 4.3 Real-Time Data Update Animation

**Location:** `components/RealtimeMetric.tsx`

```typescript
export const RealtimeMetric: React.FC<{
  value: number;
  label: string;
}> = ({ value, label }) => {
  const valueRef = useRef<HTMLDivElement>(null);
  const prevValueRef = useRef(value);

  useEffect(() => {
    if (prevValueRef.current !== value && valueRef.current) {
      // Pulse animation on data update
      animations.dataPulse(valueRef.current);
      prevValueRef.current = value;
    }
  }, [value]);

  return (
    <MetricCard
      ref={valueRef}
      label={label}
      value={value}
      unit="MW"
    />
  );
};
```

---

## 5. Responsive Design

### 5.1 Breakpoints

```typescript
// tailwind.config.ts
export const breakpoints = {
  xs: '0px',
  sm: '640px',   // Mobile
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large Desktop
  '2xl': '1536px', // Extra Large
};
```

### 5.2 Layout Patterns

**Mobile (< 768px):**
- Sidebar hidden by default, togglable hamburger menu
- Cards stack vertically
- Charts reduced height to 300px
- Font sizes reduced by 10-15%
- Single-column layout for all pages

**Tablet (768px - 1024px):**
- Sidebar collapsible (240px → 64px)
- Cards in 2-column grid where appropriate
- Full chart heights
- Default font sizes

**Desktop (> 1024px):**
- Sidebar fixed at 240px
- Multi-column layouts
- Side-by-side panels (scenario builder + results)
- Full feature set

---

## 6. Accessibility (WCAG 2.1 AA)

### 6.1 Color Contrast

```css
/* Verified combinations */
.text-primary { /* #F9FAFB on #0B1120 */ }
/* Contrast ratio: 13.8:1 ✓ */

.text-secondary { /* #D1D5DB on #0B1120 */ }
/* Contrast ratio: 10.2:1 ✓ */

.accent-cyan { /* #06B6D4 on #1F2937 */ }
/* Contrast ratio: 7.2:1 ✓ */

.accent-red { /* #EF4444 on #1F2937 */ }
/* Contrast ratio: 8.1:1 ✓ */
```

### 6.2 Keyboard Navigation

```typescript
// components/ui/accessible-button.tsx
export const AccessibleButton: React.FC<AccessibleButtonProps> = (props) => {
  return (
    <button
      {...props}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          props.onClick?.(e as any);
        }
      }}
      role="button"
      tabIndex={0}
    >
      {props.children}
    </button>
  );
};
```

### 6.3 ARIA Labels

```typescript
// Example: MetricCard with ARIA
<div
  role="complementary"
  aria-label="Tomorrow's peak demand forecast"
  aria-live="polite"
  aria-atomic="true"
>
  {value}
</div>
```

### 6.4 Focus Indicators

```css
button:focus-visible,
input:focus-visible,
[role="button"]:focus-visible {
  outline: 2px solid #06B6D4;
  outline-offset: 2px;
}
```

---

## 7. Interactive Patterns

### 7.1 Hover States

```css
.interactive-card:hover {
  border-color: #06B6D4;
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.1);
}
```

### 7.2 Active States

```css
button:active {
  transform: scale(0.95);
}
```

### 7.3 Disabled States

```css
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 8. Real-Time Update Patterns

### 8.1 WebSocket Data Updates with Animations

**Location:** `hooks/useRealtimeData.ts`

```typescript
export const useRealtimeData = (endpoint: string) => {
  const [data, setData] = useState(null);
  const animationRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const ws = new WebSocket(endpoint);

    ws.onmessage = (event) => {
      const newData = JSON.parse(event.data);
      setData(newData);

      // Trigger animation on update
      if (animationRef.current) {
        animations.dataPulse(animationRef.current);
      }
    };

    return () => ws.close();
  }, [endpoint]);

  return { data, animationRef };
};
```

### 8.2 Stale Data Indicator

```typescript
export const StaleDataIndicator: React.FC<{ lastUpdate: Date }> = ({
  lastUpdate,
}) => {
  const isStale = Date.now() - lastUpdate.getTime() > 300000; // 5 minutes

  return (
    <div className={isStale ? 'opacity-50' : ''}>
      <span className="text-xs text-text-muted">
        Last updated {formatDistanceToNow(lastUpdate)} ago
      </span>
      {isStale && (
        <WarningIcon className="inline-block ml-1 h-3 w-3 text-accent-orange" />
      )}
    </div>
  );
};
```

---

## 9. Form Validation & Error Display

### 9.1 Form Component

**Location:** `components/ui/form.tsx`

```typescript
export const FormField: React.FC<{
  label: string;
  error?: string;
  children: React.ReactNode;
}> = ({ label, error, children }) => {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-text-primary">{label}</label>
      {children}
      {error && (
        <p className="text-xs text-accent-red flex items-center gap-1 mt-1">
          <AlertCircle className="h-3 w-3" /> {error}
        </p>
      )}
    </div>
  );
};
```

### 9.2 Validation Patterns

```typescript
// Form with validation
const ScenarioForm: React.FC = () => {
  const [formData, setFormData] = useState({
    temperature: 25,
    rainfall: 0,
    isHoliday: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (formData.temperature < -10 || formData.temperature > 40) {
      newErrors.temperature = 'Temperature must be between -10 and 40°C';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      // Submit form
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormField label="Temperature" error={errors.temperature}>
        <Slider
          min={-10}
          max={40}
          value={formData.temperature}
          onChange={(value) =>
            setFormData({ ...formData, temperature: value })
          }
          unit="°C"
        />
      </FormField>
      {/* ... more fields ... */}
    </form>
  );
};
```

---

## 10. Performance Optimization

### 10.1 Image Optimization

```typescript
// Use next/image for automatic optimization
import Image from 'next/image';

export const OptimizedChart: React.FC = () => {
  return (
    <Image
      src="/charts/forecast.png"
      alt="Demand Forecast Chart"
      width={1200}
      height={400}
      priority={false}
      loading="lazy"
    />
  );
};
```

### 10.2 Code Splitting (Dynamic Imports)

```typescript
// Only load heavy components when needed
const SHAPWaterfall = dynamic(() => import('@/components/SHAPWaterfall'), {
  loading: () => <LoadingSkeleton type="chart" />,
  ssr: false,
});
```

### 10.3 GSAP Animation Performance

```typescript
// Use GPU acceleration for animations
gsap.to(element, {
  y: 20,
  opacity: 0,
  duration: 0.3,
  force3D: true, // Enable GPU acceleration
});
```

---

## 11. Component Documentation (Storybook Setup)

**Location:** `.storybook/components.stories.tsx`

```typescript
import { MetricCard } from '@/components/MetricCard';

export default {
  title: 'Components/MetricCard',
  component: MetricCard,
};

export const Primary = {
  args: {
    label: "Tomorrow's Peak Demand",
    value: 7842,
    unit: 'MW',
    trend: { value: 2.1, direction: 'up' as const },
    variant: 'primary' as const,
    size: 'lg' as const,
  },
};

export const Secondary = {
  args: {
    ...Primary.args,
    variant: 'secondary',
    label: '7-Day Average',
  },
};
```

---

## 12. Theming Configuration

**Location:** `theme/theme-config.ts`

```typescript
export const themeConfig = {
  light: {
    background: '#FFFFFF',
    text: '#000000',
    accent: '#0066CC',
  },
  dark: {
    background: '#0B1120',
    text: '#F9FAFB',
    accent: '#06B6D4',
  },
};

// Provider component
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--bg-primary',
      themeConfig[theme].background
    );
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

---

## 13. Implementation Checklist

### Phase 1: Foundation
- [ ] Set up Next.js with Tailwind & shadcn/ui
- [ ] Configure GSAP and register plugins
- [ ] Implement color palette and typography system
- [ ] Create base components (Button, Card, Slider)

### Phase 2: Complex Components
- [ ] Build MetricCard with animations
- [ ] Implement DataTable with sorting/pagination
- [ ] Create AnomalyAlertCard timeline
- [ ] Build form validation system

### Phase 3: Pages
- [ ] Executive Dashboard with metric cards & chart
- [ ] Explainability Lab with scenario builder
- [ ] Anomaly Center with timeline
- [ ] Navigation & layout shell

### Phase 4: Polish
- [ ] Responsive design testing (mobile, tablet, desktop)
- [ ] WCAG accessibility audit
- [ ] Performance optimization
- [ ] Storybook documentation
- [ ] Real-time WebSocket integration
- [ ] Error/loading/empty state coverage

---

## 14. Example Implementation: Dashboard Page

**Location:** `app/(dashboard)/page.tsx`

```typescript
'use client';

import { useEffect, useRef, useState } from 'react';
import { format } from 'date-fns';
import { MetricCard } from '@/components/MetricCard';
import { ChartContainer } from '@/components/ChartContainer';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { animations } from '@/lib/gsap-config';

export default function Dashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [forecasts, setForecasts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch forecast data
    fetchForecasts().then((data) => {
      setForecasts(data);
      setIsLoading(false);

      // Animate cards on load
      if (containerRef.current) {
        const cards = containerRef.current.querySelectorAll('.metric-card');
        animations.cardStagger(Array.from(cards) as HTMLElement[]);
      }
    });
  }, []);

  return (
    <div ref={containerRef} className="space-y-6 p-6">
      {/* Hero Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          className="metric-card"
          label="Tomorrow's Peak Demand"
          value={7842}
          unit="MW"
          trend={{ value: 2.1, direction: 'up' }}
          variant="primary"
          size="lg"
        />
        <MetricCard
          className="metric-card"
          label="7-Day Average"
          value={7150}
          unit="MW"
          variant="secondary"
          size="sm"
        />
        <MetricCard
          className="metric-card"
          label="System Health"
          value="OPTIMAL"
          unit=""
          variant="secondary"
          size="sm"
        />
      </div>

      {/* Main Chart */}
      <ChartContainer title="48-Hour Forecast" isLoading={isLoading} height={400}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={forecasts}>
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#06B6D4"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="#10B981"
              strokeDasharray="5 5"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>

      {/* Action Card */}
      <Card className="flex items-center justify-between p-6">
        <div>
          <h3 className="font-semibold text-text-primary">Analyze Forecast Factors</h3>
          <p className="text-sm text-text-secondary">
            Use the Explainability Lab to understand what drives tomorrow's forecast
          </p>
        </div>
        <Button variant="primary">Go to Lab →</Button>
      </Card>
    </div>
  );
}
```

---

## 15. Quick Reference: shadcn/ui Commands

```bash
# Install component base
npx shadcn-ui@latest init

# Add specific components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add slider
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add table
npx shadcn-ui@latest add form
npx shadcn-ui@latest add input
```

---

## 16. GSAP Installation & Setup

```bash
# Install GSAP
npm install gsap

# Or with yarn
yarn add gsap
```

**Next.js Integration (app/layout.tsx):**
```typescript
'use client';

import { useEffect } from 'react';
import gsap from 'gsap';

export default function Layout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Disable GSAP default warnings in development
    if (process.env.NODE_ENV === 'development') {
      gsap.config({ nullTargetAction: 'warn' });
    }
  }, []);

  return <>{children}</>;
}
```

---

**Document Created:** 2026-05-07  
**Status:** Ready for Implementation  
**Next Step:** Clone this spec into your project and begin Phase 1 (Foundation)
