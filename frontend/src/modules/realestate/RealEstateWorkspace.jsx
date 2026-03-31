import React, { startTransition, useDeferredValue, useEffect, useState } from "react";

import { Api } from "../../services/api";

const STATUS_OPTIONS = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "follow_up", label: "Follow Up" },
  { value: "in_progress", label: "In Progress" },
  { value: "qualified", label: "Qualified" },
  { value: "converted", label: "Converted" },
  { value: "closed", label: "Deal Closed" },
  { value: "lost", label: "Lost" },
];

const PROPERTY_TYPES = ["house", "flat", "apartment", "villa", "land", "commercial", "office", "shop", "warehouse"];
const LISTING_TYPES = ["sale", "rent", "lease"];
const FURNISHING_OPTIONS = ["unfurnished", "semi_furnished", "furnished"];

const ROLE_COPY = {
  admin: {
    title: "Command Center",
    subtitle: "Oversee listings, routing, subscriptions, and revenue across the network.",
  },
  agent: {
    title: "Agent Pipeline",
    subtitle: "Convert fresh leads into visits, closings, and wallet-ready commissions.",
  },
  customer: {
    title: "Property Journey",
    subtitle: "Discover homes, shortlist options, and coordinate visits from one workspace.",
  },
};

const NAV_ITEMS = {
  admin: ["dashboard", "leads", "properties", "deals", "agents", "reports", "settings"],
  agent: ["dashboard", "leads", "properties", "deals", "reports", "settings"],
  customer: ["dashboard", "properties", "deals", "settings"],
};

const NAV_LABELS = {
  dashboard: "Dashboard",
  leads: "Leads",
  properties: "Properties",
  deals: "Deals",
  agents: "Agents",
  reports: "Reports",
  settings: "Settings",
};

const SHOWCASE_URLS = [
  {
    label: "React Home",
    href: "http://localhost:5173/",
    description: "Public workspace preview with role-based SaaS login.",
  },
  {
    label: "React Login",
    href: "http://localhost:5173/accounts/login/",
    description: "Same React login routed through the accounts path.",
  },
  {
    label: "Django Dashboard",
    href: "http://127.0.0.1:9000/accounts/dashboard/",
    description: "Server-rendered dashboard for demoing the platform on Django.",
  },
];

const DEMO_USERS = [
  {
    label: "Agent Demo",
    role: "agent",
    email: "agent@example.com",
    password: "Agent@123",
    caption: "Best for seeing leads, profile, wallet, visits, profile, and settings in one dashboard.",
  },
  {
    label: "Admin Demo",
    role: "admin",
    email: "admin@example.com",
    password: "Admin@123",
    caption: "Control listings, agents, analytics, and approvals from the command center.",
  },
  {
    label: "Customer Demo",
    role: "customer",
    email: "customer@example.com",
    password: "Customer@123",
    caption: "Browse marketplace, save wishlist, schedule visits, and raise enquiries.",
  },
];

const PUBLIC_FEATURE_GROUPS = [
  {
    title: "Marketplace + CRM",
    summary: "Daily operating stack for property discovery, lead handling, and agent productivity.",
    items: [
      "Property marketplace with comparison, wishlist, visit scheduling, and owner or agent listings.",
      "Lead capture from website forms, ad campaigns, WhatsApp chat, manual entry, and missed calls.",
      "Round-robin location routing using pin code, district, and state matching.",
      "CRM stages for new lead, contacted, follow-up, visit, negotiation, closed, and lost.",
    ],
  },
  {
    title: "Agent Growth + Revenue",
    summary: "Everything an agent needs from onboarding to payout visibility.",
    items: [
      "Agent profile, coverage areas, approval status, KYC verification, franchise hierarchy, and service zones.",
      "Wallet balance, lead purchase flows, subscription plans, commission credit, and withdrawal requests.",
      "Property posting, visit coordination, call logging, and notification-driven follow-ups.",
      "Web dashboard plus mobile-ready API foundation for Flutter app workflows.",
    ],
  },
  {
    title: "Intelligence + Automation",
    summary: "Advanced modules that turn the CRM into a real-estate intelligence platform.",
    items: [
      "Property aggregation engine with import batches, normalization, duplicate detection, and enrichment.",
      "Demand heatmaps, price trend analytics, top investment zones, and builder project visibility.",
      "AI voice lead qualification, premium lead marketplace, investor matching, and property alerts.",
      "Document vault, fraud checks, role-based security, notifications, and multi-tenant SaaS readiness.",
    ],
  },
];

const ROLE_DEMO_STEPS = {
  admin: [
    { view: "agents", title: "Approve agent coverage", detail: "Review mapped cities, pin codes, KYC, and franchise ownership before activating the field network." },
    { view: "listings", title: "Moderate inventory", detail: "Approve or reject newly posted properties and aggregated listings before they go live." },
    { view: "analytics", title: "Inspect intelligence", detail: "Open heatmaps, price trends, investor signals, and channel performance for the tenant." },
    { view: "messages", title: "Track automation", detail: "See notifications, call logs, and communication workflows triggered by leads and visits." },
  ],
  agent: [
    { view: "profile", title: "Open agent profile", detail: "Check identity, license, KYC, coverage area, ratings, wallet, and live operating readiness." },
    { view: "leads", title: "Capture and qualify leads", detail: "Add enquiries, update pipeline stages, log calls, and follow up from a single CRM board." },
    { view: "marketplace", title: "Show inventory to buyers", detail: "Compare listings, send WhatsApp-ready properties, and schedule field visits." },
    { view: "wallet", title: "Track earnings", detail: "See lead purchase history, commissions, withdrawals, and subscription-linked selling capacity." },
    { view: "settings", title: "Review automation settings", detail: "See security, communication, integrations, web-app access, and demo links in one place." },
  ],
  customer: [
    { view: "marketplace", title: "Search the marketplace", detail: "Browse active listings, compare options, and open builder or locality opportunities." },
    { view: "wishlist", title: "Save shortlisted homes", detail: "Create a shortlist and keep favorite properties ready for quick comparison." },
    { view: "visits", title: "Schedule site visits", detail: "Book walkthroughs that automatically create CRM activity for the assigned agent." },
    { view: "profile", title: "Review profile and preferences", detail: "Check budget, location fit, saved behavior, and account identity in one place." },
  ],
};

const ROLE_FEATURE_TRACKS = {
  admin: [
    {
      title: "Tenant Operations",
      summary: "Everything visible for company-wide governance.",
      items: ["Agent approvals and area assignment", "Lead distribution rules and reassignment", "Listing moderation and builder marketplace", "Subscriptions, payouts, and fraud review"],
    },
    {
      title: "Intelligence Layer",
      summary: "High-level monitoring for the complete SaaS platform.",
      items: ["Demand heatmaps and price trends", "Property aggregation pipeline", "Investor opportunity matching", "Campaign and revenue analytics"],
    },
  ],
  agent: [
    {
      title: "Agent Workbench",
      summary: "Visible from profile to settings for the field team.",
      items: ["Profile, KYC, service area, rating, and coverage health", "Lead queue, call logs, follow-ups, and visit scheduling", "Marketplace listings, builder projects, and brochure-ready inventory", "Wallet, commissions, premium leads, and subscription limits"],
    },
    {
      title: "Automation + Intelligence",
      summary: "Modules that support faster selling and smarter targeting.",
      items: ["AI voice lead qualification", "Demand heatmaps and price trend signals", "Investor matches and builder launch tracking", "Alerts, documents, and fraud-safe workflows"],
    },
  ],
  customer: [
    {
      title: "Buyer / Seller Journey",
      summary: "Personal workspace for discovery and coordination.",
      items: ["Marketplace search and advanced filtering", "Wishlist, comparisons, and visit booking", "Direct listing upload for owners", "Alerts, messages, and wallet-ready services"],
    },
    {
      title: "Guided Intelligence",
      summary: "Features that help customers make better decisions.",
      items: ["Budget-fit discovery", "Builder project exploration", "Locality price awareness", "Agent-assisted communication and reminders"],
    },
  ],
};

const ROLE_SETTINGS_CARDS = {
  admin: [
    { title: "Security", items: ["JWT authentication", "OTP login ready in Django auth", "Role-based permissions", "Tenant-scoped data isolation"] },
    { title: "Automation", items: ["Lead routing via location rules", "Notification fanout", "Email, SMS, WhatsApp, and call workflows", "Celery + Redis background processing"] },
    { title: "Platform Access", items: ["React web workspace", "Django fallback dashboard", "API-first architecture", "Mobile app integration path"] },
  ],
  agent: [
    { title: "Profile Controls", items: ["Personal identity and mobile", "License, KYC, and approval status", "Primary city, district, state, and pin code", "Franchise and team visibility"] },
    { title: "Automation Channels", items: ["CRM call logging", "WhatsApp-ready listing sharing", "Email and SMS alert hooks", "AI voice qualification support"] },
    { title: "Workspace Access", items: ["Web dashboard on React", "Django account dashboard", "Profile editing path", "Mobile-ready SaaS architecture"] },
  ],
  customer: [
    { title: "Account", items: ["Identity, contact info, and preferences", "Saved budget and locality interests", "Wishlist visibility and visit history", "Secure login and tenant access"] },
    { title: "Alerts", items: ["New property alerts", "Price drop notifications", "Builder launch awareness", "WhatsApp, email, SMS, and in-app support"] },
    { title: "Experience", items: ["Responsive web dashboard", "Flutter-ready mobile support", "Agent-assisted messaging", "Property document workflow support"] },
  ],
};

function resolveRoleGroup(user) {
  const role = String(user?.role || "").toLowerCase();
  if (user?.is_superuser || user?.is_staff || ["super_admin", "state_admin", "district_admin", "area_admin"].includes(role)) {
    return "admin";
  }
  if (["agent", "super_agent"].includes(role)) {
    return "agent";
  }
  return "customer";
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(Number(value || 0));
}

function formatDateTime(value) {
  if (!value) return "-";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch (error) {
    return value;
  }
}

function badgeTone(value) {
  const tone = String(value || "").toLowerCase();
  if (["closed", "won", "approved", "active", "success", "hot"].includes(tone)) return "crm-badge crm-badge-success";
  if (["pending", "visit_scheduled", "in_progress", "warm"].includes(tone)) return "crm-badge crm-badge-warn";
  if (["lost", "rejected", "error", "cold", "danger"].includes(tone)) return "crm-badge crm-badge-danger";
  return "crm-badge crm-badge-neutral";
}

function normalizeList(payload) {
  return Api.normalizeList(payload);
}

function LoginPanel({ form, setForm, error, busy, onSubmit, onUseDemoUser, pathname }) {
  return (
    <div className="crm-auth-wrap">
      <div className="crm-auth-card crm-auth-card-showcase">
        <div className="crm-auth-copy">
          <p className="crm-kicker">Real Estate SaaS</p>
          <h1>Marketplace, CRM, wallet, and automation in one control room.</h1>
          <p>
            Ye login preview ab sirf form nahi hai. Yahin se aap dekh sakte ho ki platform me marketplace, CRM, wallet,
            automation, intelligence, builder marketplace, investor matching, aur agent operating stack sab kaha visible
            hoga.
          </p>
          <div className="crm-auth-points">
            <span>Lead automation</span>
            <span>Agent network</span>
            <span>Wallet payouts</span>
            <span>Mobile-ready CRM</span>
            <span>Builder projects</span>
            <span>AI voice</span>
            <span>Demand heatmaps</span>
            <span>Investor matching</span>
          </div>
          <div className="crm-auth-demo-grid">
            {DEMO_USERS.map((user) => (
              <button key={user.email} className="crm-auth-demo-btn" type="button" onClick={() => onUseDemoUser(user)}>
                <strong>{user.label}</strong>
                <small>{user.email}</small>
                <small>{user.caption}</small>
              </button>
            ))}
          </div>
          <div className="crm-auth-route-list">
            {SHOWCASE_URLS.map((item) => (
              <a key={item.href} className="crm-auth-route-card" href={item.href}>
                <strong>{item.label}</strong>
                <code>{item.href}</code>
                <small>{item.description}</small>
              </a>
            ))}
          </div>
          <div className="crm-auth-module-grid">
            {PUBLIC_FEATURE_GROUPS.map((group) => (
              <article key={group.title} className="crm-auth-module-card">
                <strong>{group.title}</strong>
                <p>{group.summary}</p>
                <ul>
                  {group.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
          <div className="crm-auth-flow">
            <div className="crm-section-head">
              <div>
                <h2>Demo Flow</h2>
                <p>Sabse easy समझने वाला walkthrough: agent login se settings tak.</p>
              </div>
            </div>
            {ROLE_DEMO_STEPS.agent.map((step, index) => (
              <div key={step.title} className="crm-auth-flow-step">
                <span>{index + 1}</span>
                <div>
                  <strong>{step.title}</strong>
                  <small>{step.detail}</small>
                </div>
              </div>
            ))}
          </div>
        </div>
        <form className="crm-auth-form" onSubmit={onSubmit}>
          <div className="crm-auth-form-head">
            <p className="crm-kicker">Workspace Access</p>
            <h2>{pathname === "/accounts/login/" ? "Accounts Login Preview" : "Role-Based Login"}</h2>
            <p className="crm-muted-text">
              Current route: <code>{pathname}</code>
            </p>
          </div>
          <label>
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              placeholder="admin@example.com"
              required
            />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="Enter your password"
              required
            />
          </label>
          {error ? <div className="crm-inline-error">{error}</div> : null}
          <div className="crm-auth-credentials">
            {DEMO_USERS.map((user) => (
              <button key={user.role} className="crm-secondary-btn" type="button" onClick={() => onUseDemoUser(user)}>
                Use {user.label}
              </button>
            ))}
          </div>
          <button className="crm-primary-btn" type="submit" disabled={busy}>
            {busy ? "Signing In..." : "Enter Workspace"}
          </button>
          <div className="crm-auth-note">
            Agent dashboard me login ke baad `Services`, `Demo Flow`, `Profile`, aur `Settings` tabs me saare major
            modules clearly visible rahenge.
          </div>
          <div className="crm-auth-links">
            <a href="/accounts/signup/">Create account</a>
            <a href="/accounts/login/">Open Django auth</a>
          </div>
        </form>
      </div>
    </div>
  );
}

function SectionCard({ title, subtitle, action, children }) {
  return (
    <section className="crm-section-card">
      <div className="crm-section-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {action ? <div>{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

function StatStrip({ items }) {
  return (
    <div className="crm-stat-grid">
      {items.map((item) => (
        <div className="crm-stat-card" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.caption}</small>
        </div>
      ))}
    </div>
  );
}

function HeroPanel({ roleGroup, me, summary, dashboard, viewport, onRefresh, onLogout }) {
  const copy = ROLE_COPY[roleGroup];
  return (
    <section className={`crm-hero crm-hero-${viewport}`}>
      <div>
        <p className="crm-kicker">{roleGroup === "customer" ? "Customer Workspace" : roleGroup === "agent" ? "Agent Workspace" : "Admin Workspace"}</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
        <div className="crm-hero-pills">
          <span>{me?.company_name || "Independent tenant"}</span>
          <span>{dashboard?.total_leads || summary?.leads_total || 0} leads</span>
          <span>{formatCurrency(summary?.revenue || dashboard?.total_revenue)}</span>
        </div>
      </div>
      <div className="crm-hero-actions">
        <button className="crm-secondary-btn" type="button" onClick={onRefresh}>
          Refresh
        </button>
        <button className="crm-secondary-btn" type="button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </section>
  );
}

function FeatureTrackPanel({ tracks, onJump }) {
  return (
    <SectionCard
      title="Feature Map"
      subtitle="Yahan se clear dikhega ki current role ko platform ke kaun kaun se modules mil rahe hain."
      action={
        <button className="crm-secondary-btn" type="button" onClick={() => onJump("reports")}>
          Open Reports
        </button>
      }
    >
      <div className="crm-feature-grid">
        {tracks.map((track) => (
          <article key={track.title} className="crm-feature-card">
            <span className="crm-kicker">{track.title}</span>
            <h3>{track.summary}</h3>
            <ul>
              {track.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}

function ServicesPanel({ groups, onJump }) {
  return (
    <div className="crm-stack">
      {groups.map((group) => (
        <SectionCard key={group.title} title={group.title} subtitle={group.subtitle}>
          <div className="crm-feature-grid">
            {group.cards.map((card) => (
              <article key={card.title} className="crm-feature-card crm-service-card">
                <div className="crm-service-top">
                  <span className="crm-kicker">{card.eyebrow}</span>
                  <span className={badgeTone(card.statusTone || "active")}>{card.statusLabel}</span>
                </div>
                <h3>{card.title}</h3>
                <strong className="crm-service-value">{card.value}</strong>
                <p>{card.description}</p>
                <button className="crm-secondary-btn" type="button" onClick={() => onJump(card.view)}>
                  {card.cta || `Open ${NAV_LABELS[card.view] || "Module"}`}
                </button>
              </article>
            ))}
          </div>
        </SectionCard>
      ))}
    </div>
  );
}

function DemoFlowPanel({ steps, onJump, roleGroup }) {
  return (
    <SectionCard
      title="Demo Flow"
      subtitle={`Step-by-step walkthrough for the ${roleGroup} journey so every feature becomes easy to understand.`}
    >
      <div className="crm-flow-list">
        {steps.map((step, index) => (
          <button key={step.title} className="crm-flow-step" type="button" onClick={() => onJump(step.view)}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <small>{step.detail}</small>
            </div>
          </button>
        ))}
      </div>
    </SectionCard>
  );
}

function ProfilePanel({ roleGroup, me, agentProfile, wallet, subscriptions, dashboard, leads, visits, properties, onJump }) {
  const currentSubscription = subscriptions.find((entry) => String(entry.status || "").toLowerCase() === "active") || subscriptions[0];
  const coverageText = [agentProfile?.city, agentProfile?.district, agentProfile?.state, agentProfile?.pin_code].filter(Boolean).join(", ");

  return (
    <div className="crm-grid-2">
      <SectionCard title="Profile" subtitle="Identity, operating scope, coverage, and selling readiness.">
        <div className="crm-profile-grid">
          <div className="crm-profile-card">
            <span>Workspace User</span>
            <strong>{me?.first_name || me?.username || me?.email || "Workspace User"}</strong>
            <small>{me?.email || "No email on file"}</small>
          </div>
          <div className="crm-profile-card">
            <span>Role</span>
            <strong>{roleGroup === "agent" ? "Agent" : roleGroup === "admin" ? "Admin" : "Customer"}</strong>
            <small>{me?.company_name || "Independent tenant"}</small>
          </div>
          <div className="crm-profile-card">
            <span>Wallet</span>
            <strong>{formatCurrency(wallet?.balance || me?.wallet_balance || 0)}</strong>
            <small>{currentSubscription?.plan_name || currentSubscription?.plan_display || "Plan not linked yet"}</small>
          </div>
          <div className="crm-profile-card">
            <span>Activity</span>
            <strong>{formatCompactNumber(leads.length + visits.length + properties.length)}</strong>
            <small>{`${leads.length} leads, ${visits.length} visits, ${properties.length} listings`}</small>
          </div>
        </div>

        {roleGroup === "agent" ? (
          <div className="crm-profile-detail-list">
            <div><span>Approval</span><strong>{agentProfile?.approval_status || "pending"}</strong></div>
            <div><span>KYC</span><strong>{agentProfile?.kyc_verified ? "Verified" : "Pending"}</strong></div>
            <div><span>License</span><strong>{agentProfile?.license_number || "Not added yet"}</strong></div>
            <div><span>Coverage</span><strong>{coverageText || "Map city, district, state, and pin code"}</strong></div>
            <div><span>Experience</span><strong>{agentProfile?.experience_years || 0} years</strong></div>
            <div><span>Performance</span><strong>{formatCurrency(agentProfile?.total_sales || 0)} sales</strong></div>
          </div>
        ) : null}

        <div className="crm-inline-actions crm-top-gap">
          <a className="crm-secondary-btn" href="/accounts/edit-profile/">
            Edit Django Profile
          </a>
          <button className="crm-secondary-btn" type="button" onClick={() => onJump("settings")}>
            Open Settings
          </button>
        </div>
      </SectionCard>

      <SectionCard title="Role Snapshot" subtitle="Quick look at what this dashboard is responsible for right now.">
        <div className="crm-mini-list">
          <div className="crm-mini-item">
            <div>
              <strong>Lead Coverage</strong>
              <small>{roleGroup === "agent" ? "Assigned enquiries, routing visibility, follow-up cadence." : "Pipeline and conversion visibility across the workspace."}</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{dashboard?.total_leads || leads.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Inventory Scope</strong>
              <small>{roleGroup === "customer" ? "Saved and discoverable listings for your current journey." : "Inventory visible for moderation, pitching, or selling."}</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{properties.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Visit Coordination</strong>
              <small>Site visits, property walkthroughs, and CRM activity linked to each opportunity.</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{visits.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Revenue Readiness</strong>
              <small>Wallet balance, commissions, plan access, and operating capacity for this role.</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{formatCurrency(wallet?.balance || me?.wallet_balance || 0)}</span>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function SettingsPanel({ cards, notifications, calls, voiceCalls, onJump }) {
  return (
    <div className="crm-stack">
      <SectionCard title="Settings + Access Map" subtitle="Yahan se samajh aata hai ki security, automation, integrations, aur device access kaise structured hai.">
        <div className="crm-feature-grid">
          {cards.map((card) => (
            <article key={card.title} className="crm-feature-card">
              <span className="crm-kicker">{card.title}</span>
              <ul>
                {card.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </SectionCard>

      <div className="crm-grid-2">
        <SectionCard title="Connected Routes" subtitle="Useful demo URLs so you can compare React and Django views side by side.">
          <div className="crm-route-grid">
            {SHOWCASE_URLS.map((item) => (
              <a key={item.href} className="crm-route-card" href={item.href}>
                <strong>{item.label}</strong>
                <code>{item.href}</code>
                <small>{item.description}</small>
              </a>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="Communication State"
          subtitle="Notification and call-ready modules connected to this workspace."
          action={
            <button className="crm-secondary-btn" type="button" onClick={() => onJump("reports")}>
              Open Reports
            </button>
          }
        >
          <div className="crm-mini-list">
            <div className="crm-mini-item">
              <div>
                <strong>In-app notifications</strong>
                <small>Unread alerts, workflow nudges, and assignment messages.</small>
              </div>
              <span className="crm-badge crm-badge-neutral">{notifications.filter((item) => !item.read_at).length}</span>
            </div>
            <div className="crm-mini-item">
              <div>
                <strong>CRM call logs</strong>
                <small>Click-to-call, missed call, and manual call activity.</small>
              </div>
              <span className="crm-badge crm-badge-neutral">{calls.length}</span>
            </div>
            <div className="crm-mini-item">
              <div>
                <strong>AI voice qualification</strong>
                <small>Structured bot-led conversations and transcripts for new leads.</small>
              </div>
              <span className="crm-badge crm-badge-neutral">{voiceCalls.length}</span>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

function LeadComposer({ form, setForm, onSubmit, busy, roleGroup }) {
  return (
    <SectionCard
      title={roleGroup === "customer" ? "Request Property Help" : "Capture Lead"}
      subtitle="Add fresh leads from website forms, campaigns, referrals, or manual outreach."
    >
      <form className="crm-form-grid" onSubmit={onSubmit}>
        <input placeholder="Name" value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
        <input placeholder="Phone" value={form.phone} onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))} required />
        <input placeholder="Email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
        <input placeholder="Budget" type="number" value={form.budget} onChange={(event) => setForm((prev) => ({ ...prev, budget: event.target.value }))} />
        <select value={form.property_type} onChange={(event) => setForm((prev) => ({ ...prev, property_type: event.target.value }))}>
          <option value="">Property Type</option>
          {PROPERTY_TYPES.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <input placeholder="City" value={form.city} onChange={(event) => setForm((prev) => ({ ...prev, city: event.target.value }))} />
        <input placeholder="District" value={form.district} onChange={(event) => setForm((prev) => ({ ...prev, district: event.target.value }))} />
        <input placeholder="State" value={form.state} onChange={(event) => setForm((prev) => ({ ...prev, state: event.target.value }))} />
        <input placeholder="Pin Code" value={form.pincode} onChange={(event) => setForm((prev) => ({ ...prev, pincode: event.target.value }))} />
        <select value={form.source} onChange={(event) => setForm((prev) => ({ ...prev, source: event.target.value }))}>
          {["website", "facebook_ads", "instagram_ads", "google_ads", "whatsapp_chatbot", "landing_page", "manual", "referral"].map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <textarea
          className="crm-form-span"
          placeholder="Notes"
          value={form.notes}
          onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
        />
        <button className="crm-primary-btn crm-form-button" type="submit" disabled={busy}>
          {busy ? "Saving..." : "Create Lead"}
        </button>
      </form>
    </SectionCard>
  );
}

function LeadTable({
  leads,
  agents,
  roleGroup,
  onStatusChange,
  onAssign,
  onCallLog,
  selectedIds = [],
  selectedLeadId = null,
  onToggleSelect,
  onSelectAll,
  onSelectLead,
  onConvert,
  onContact,
}) {
  if (!leads.length) {
    return <div className="crm-empty-state">No leads match the current view yet.</div>;
  }

  return (
    <div className="crm-table-wrap">
      <table className="crm-table">
        <thead>
          <tr>
            <th>
              <input type="checkbox" checked={selectedIds.length === leads.length} onChange={() => onSelectAll?.()} />
            </th>
            <th>Lead</th>
            <th>Location</th>
            <th>Budget</th>
            <th>Status</th>
            <th>Agent</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.id} className={selectedLeadId === lead.id ? "is-active" : ""}>
              <td>
                <input type="checkbox" checked={selectedIds.includes(lead.id)} onChange={() => onToggleSelect?.(lead.id)} />
              </td>
              <td>
                <button className="crm-link-button" type="button" onClick={() => onSelectLead?.(lead)}>
                  <strong>{lead.name || lead.mobile}</strong>
                </button>
                <small>{lead.mobile || lead.email || "-"}</small>
              </td>
              <td>
                <strong>{lead.city || lead.preferred_location || "-"}</strong>
                <small>
                  {[lead.district, lead.state, lead.pincode_text].filter(Boolean).join(", ") || "Unspecified coverage"}
                </small>
              </td>
              <td>{formatCurrency(lead.budget || lead.deal_value)}</td>
              <td>
                <span className={badgeTone(lead.status)}>{lead.status || "new"}</span>
                <small>{lead.distribution_level ? `Matched on ${lead.distribution_level}` : "Awaiting distribution"}</small>
              </td>
              <td>
                <strong>{lead.assigned_agent_name || "Unassigned"}</strong>
                <small>{lead.source || "manual"}</small>
              </td>
              <td>
                <div className="crm-inline-actions">
                  <select defaultValue="" onChange={(event) => onStatusChange(lead, event.target.value)}>
                    <option value="" disabled>
                      Update
                    </option>
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {roleGroup !== "customer" ? (
                    <button className="crm-secondary-btn" type="button" onClick={() => onCallLog(lead)}>
                      Log Call
                    </button>
                  ) : null}
                  {roleGroup !== "customer" ? (
                    <button className="crm-secondary-btn" type="button" onClick={() => onContact?.(lead, "whatsapp")}>
                      WhatsApp
                    </button>
                  ) : null}
                  {roleGroup !== "customer" ? (
                    <button className="crm-secondary-btn" type="button" onClick={() => onContact?.(lead, "email")}>
                      Email
                    </button>
                  ) : null}
                  {roleGroup !== "customer" ? (
                    <button className="crm-primary-btn" type="button" onClick={() => onConvert?.(lead)}>
                      Convert
                    </button>
                  ) : null}
                  {roleGroup === "admin" ? (
                    <select defaultValue="" onChange={(event) => onAssign(lead, event.target.value)}>
                      <option value="" disabled>
                        Assign
                      </option>
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name || agent.user_email || `Agent ${agent.id}`}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LeadOpsPanel({
  agents,
  selectedLeadIds,
  bulkAgentId,
  setBulkAgentId,
  bulkAutoAssign,
  setBulkAutoAssign,
  onBulkAssign,
  csvImportFile,
  setCsvImportFile,
  onCsvImport,
  importBatches,
  leadSources,
}) {
  return (
    <div className="crm-grid-2">
      <SectionCard title="Bulk Actions" subtitle="Assign, rebalance, and import leads without leaving the pipeline.">
        <div className="crm-inline-actions crm-top-gap">
          <input value={selectedLeadIds.length} readOnly />
          <select value={bulkAgentId} onChange={(event) => setBulkAgentId(event.target.value)} disabled={bulkAutoAssign}>
            <option value="">Select agent</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name || agent.user_email || `Agent ${agent.id}`}
              </option>
            ))}
          </select>
          <label className="crm-inline-check">
            <input type="checkbox" checked={bulkAutoAssign} onChange={(event) => setBulkAutoAssign(event.target.checked)} />
            <span>Auto assign</span>
          </label>
          <button className="crm-primary-btn" type="button" onClick={onBulkAssign}>
            Run Bulk Action
          </button>
        </div>
        <div className="crm-mini-list crm-top-gap">
          {leadSources.slice(0, 4).map((source) => (
            <div className="crm-mini-item" key={source.id}>
              <div>
                <strong>{source.name}</strong>
                <small>{source.kind}</small>
              </div>
              <span className={badgeTone(source.is_active ? "success" : "danger")}>{source.source_value}</span>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="CSV Import" subtitle="Website, ad, and broker spreadsheets can enter the engine here.">
        <form className="crm-form-grid" onSubmit={onCsvImport}>
          <input type="file" accept=".csv" onChange={(event) => setCsvImportFile(event.target.files?.[0] || null)} />
          <button className="crm-primary-btn crm-form-button" type="submit">
            Import CSV
          </button>
        </form>
        <div className="crm-mini-list crm-top-gap">
          {importBatches.slice(0, 5).map((batch) => (
            <div className="crm-mini-item" key={batch.id}>
              <div>
                <strong>{batch.source_name || batch.source_display || batch.import_type}</strong>
                <small>{batch.created_leads} created • {batch.duplicate_rows} duplicates • {batch.failed_rows} failed</small>
              </div>
              <span className={badgeTone(batch.status)}>{batch.status}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function LeadTimelinePanel({ lead, timeline }) {
  if (!lead) {
    return <div className="crm-empty-state">Select a lead from the list to open its detail timeline.</div>;
  }

  return (
    <SectionCard title="Lead Detail" subtitle="Timeline, assigned agent, and latest workflow context for the selected enquiry.">
      <div className="crm-profile-grid">
        <div className="crm-profile-card">
          <span>Lead</span>
          <strong>{lead.name || lead.mobile}</strong>
          <small>{lead.mobile || lead.email || "-"}</small>
        </div>
        <div className="crm-profile-card">
          <span>Status</span>
          <strong>{lead.status}</strong>
          <small>{lead.stage}</small>
        </div>
        <div className="crm-profile-card">
          <span>Assigned Agent</span>
          <strong>{lead.assigned_agent_name || "Unassigned"}</strong>
          <small>{lead.assigned_agent_phone || "No phone available"}</small>
        </div>
        <div className="crm-profile-card">
          <span>Lead Score</span>
          <strong>{lead.lead_score || lead.score || 0}</strong>
          <small>{lead.temperature || "warm"}</small>
        </div>
      </div>
      <div className="crm-mini-list crm-top-gap">
        {timeline.length ? (
          timeline.map((entry) => (
            <div className="crm-mini-item" key={entry.id}>
              <div>
                <strong>{entry.title}</strong>
                <small>{entry.body || "Workflow event logged."}</small>
              </div>
              <span className="crm-badge crm-badge-neutral">{formatDateTime(entry.timestamp)}</span>
            </div>
          ))
        ) : (
          <div className="crm-empty-state slim">Timeline is empty for this lead.</div>
        )}
      </div>
    </SectionCard>
  );
}

function KanbanBoard({ columns, onStatusChange }) {
  return (
    <SectionCard title="Kanban Pipeline" subtitle="Move enquiries across the real-estate funnel from new to converted.">
      <div className="crm-feature-grid">
        {columns.map((column) => (
          <article key={column.stage} className="crm-feature-card">
            <div className="crm-service-top">
              <span className="crm-kicker">{column.label}</span>
              <span className="crm-badge crm-badge-neutral">{column.count}</span>
            </div>
            <div className="crm-mini-list">
              {(column.leads || []).slice(0, 6).map((lead) => (
                <div className="crm-mini-item" key={lead.id}>
                  <div>
                    <strong>{lead.name || lead.mobile}</strong>
                    <small>{lead.city || lead.district || lead.state || "-"}</small>
                  </div>
                  <select defaultValue="" onChange={(event) => onStatusChange(lead, event.target.value)}>
                    <option value="" disabled>
                      Move
                    </option>
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}

function DealsPanel({ roleGroup, deals, dealPayments, customerDashboard, onApprovePayment, onMarkPaymentPaid }) {
  return (
    <div className="crm-stack">
      <SectionCard title="Deals" subtitle="Converted enquiries, deal values, and payout readiness.">
        {deals.length ? (
          <div className="crm-table-wrap">
            <table className="crm-table">
              <thead>
                <tr>
                  <th>Deal</th>
                  <th>Customer</th>
                  <th>Agent</th>
                  <th>Amount</th>
                  <th>Commission</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((deal) => (
                  <tr key={deal.id}>
                    <td>
                      <strong>{deal.lead_name || `Deal #${deal.id}`}</strong>
                      <small>{deal.property_title || "Property TBD"}</small>
                    </td>
                    <td>
                      <strong>{deal.customer_name || "Customer pending"}</strong>
                      <small>{deal.closing_date || "-"}</small>
                    </td>
                    <td>
                      <strong>{deal.agent_name || "-"}</strong>
                      <small>{deal.stage}</small>
                    </td>
                    <td>{formatCurrency(deal.deal_amount)}</td>
                    <td>{formatCurrency(deal.commission_amount)}</td>
                    <td><span className={badgeTone(deal.status)}>{deal.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="crm-empty-state">No deals available yet.</div>
        )}
      </SectionCard>

      <SectionCard title="Payments" subtitle="Admin payout control and payment lifecycle tracking.">
        <div className="crm-mini-list">
          {dealPayments.length ? (
            dealPayments.map((payment) => (
              <div className="crm-mini-item" key={payment.id}>
                <div>
                  <strong>{payment.payment_type.replaceAll("_", " ")}</strong>
                  <small>{payment.agent_name || payment.reference || "Payment record"}</small>
                </div>
                <div className="crm-inline-actions">
                  <span className={badgeTone(payment.status)}>{formatCurrency(payment.amount)}</span>
                  {roleGroup === "admin" && payment.status === "pending" ? (
                    <button className="crm-secondary-btn" type="button" onClick={() => onApprovePayment(payment.id)}>
                      Approve
                    </button>
                  ) : null}
                  {roleGroup === "admin" && payment.status !== "paid" ? (
                    <button className="crm-secondary-btn" type="button" onClick={() => onMarkPaymentPaid(payment.id)}>
                      Mark Paid
                    </button>
                  ) : null}
                </div>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">No payment records yet.</div>
          )}
        </div>
      </SectionCard>

      {roleGroup === "customer" && customerDashboard ? (
        <SectionCard title="Customer Dashboard" subtitle="Inquiry status, nearby properties, and assigned agent contact.">
          <div className="crm-profile-grid">
            <div className="crm-profile-card">
              <span>Inquiry Status</span>
              <strong>{customerDashboard.lead?.status || "No active inquiry"}</strong>
              <small>{customerDashboard.lead?.stage || "Waiting"}</small>
            </div>
            <div className="crm-profile-card">
              <span>Assigned Agent</span>
              <strong>{customerDashboard.assigned_agent?.name || "Pending"}</strong>
              <small>{customerDashboard.assigned_agent?.phone || "No phone yet"}</small>
            </div>
          </div>
          <MarketplaceGrid
            properties={customerDashboard.nearby_properties || []}
            roleGroup={roleGroup}
            compareIds={[]}
            onToggleCompare={() => {}}
            onToggleWishlist={() => {}}
            onScheduleVisit={() => {}}
          />
        </SectionCard>
      ) : null}
    </div>
  );
}

function PropertyComposer({ form, setForm, onSubmit, busy }) {
  return (
    <SectionCard title="Post Property" subtitle="Publish sale or rental inventory for the marketplace and your CRM pipeline.">
      <form className="crm-form-grid" onSubmit={onSubmit}>
        <input placeholder="Title" value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} required />
        <input placeholder="Price" type="number" value={form.price} onChange={(event) => setForm((prev) => ({ ...prev, price: event.target.value }))} required />
        <select value={form.listing_type} onChange={(event) => setForm((prev) => ({ ...prev, listing_type: event.target.value }))}>
          {LISTING_TYPES.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <select value={form.property_type} onChange={(event) => setForm((prev) => ({ ...prev, property_type: event.target.value }))}>
          {PROPERTY_TYPES.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <input placeholder="Area (sqft)" type="number" value={form.area_sqft} onChange={(event) => setForm((prev) => ({ ...prev, area_sqft: event.target.value }))} />
        <input placeholder="Bedrooms" type="number" value={form.bedrooms} onChange={(event) => setForm((prev) => ({ ...prev, bedrooms: event.target.value }))} />
        <input placeholder="Bathrooms" type="number" value={form.bathrooms} onChange={(event) => setForm((prev) => ({ ...prev, bathrooms: event.target.value }))} />
        <select value={form.furnishing} onChange={(event) => setForm((prev) => ({ ...prev, furnishing: event.target.value }))}>
          {FURNISHING_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <input placeholder="City" value={form.city} onChange={(event) => setForm((prev) => ({ ...prev, city: event.target.value }))} required />
        <input placeholder="District" value={form.district} onChange={(event) => setForm((prev) => ({ ...prev, district: event.target.value }))} />
        <input placeholder="State" value={form.state} onChange={(event) => setForm((prev) => ({ ...prev, state: event.target.value }))} />
        <input placeholder="Pin Code" value={form.pin_code} onChange={(event) => setForm((prev) => ({ ...prev, pin_code: event.target.value }))} />
        <input placeholder="Locality / Address" className="crm-form-span" value={form.location} onChange={(event) => setForm((prev) => ({ ...prev, location: event.target.value }))} />
        <textarea
          className="crm-form-span"
          placeholder="Describe highlights, amenities, neighborhood, or brochure copy"
          value={form.description}
          onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
        />
        <button className="crm-primary-btn crm-form-button" type="submit" disabled={busy}>
          {busy ? "Publishing..." : "Publish Listing"}
        </button>
      </form>
    </SectionCard>
  );
}

function MarketplaceGrid({ properties, roleGroup, compareIds, onToggleCompare, onToggleWishlist, onScheduleVisit }) {
  if (!properties.length) {
    return <div className="crm-empty-state">No properties found for the current filters.</div>;
  }

  return (
    <div className="crm-property-grid">
      {properties.map((property) => {
        const selected = compareIds.includes(property.id);
        return (
          <article className="crm-property-card" key={property.id}>
            <div className="crm-property-media">
              <span className={badgeTone(property.status)}>{property.status || "pending_approval"}</span>
              <span className="crm-property-price">{formatCurrency(property.price)}</span>
            </div>
            <div className="crm-property-copy">
              <h3>{property.title}</h3>
              <p>{property.description || "Modern listing waiting for brochure-ready copy."}</p>
              <div className="crm-property-meta">
                <span>{property.property_type}</span>
                <span>{property.listing_type}</span>
                <span>{property.city}</span>
                <span>{property.bedrooms || 0} bed</span>
                <span>{property.bathrooms || 0} bath</span>
              </div>
              <div className="crm-inline-actions">
                <button className="crm-secondary-btn" type="button" onClick={() => onToggleCompare(property.id)}>
                  {selected ? "Remove Compare" : "Compare"}
                </button>
                <button className="crm-secondary-btn" type="button" onClick={() => onToggleWishlist(property.id)}>
                  {property.is_wishlisted ? "Wishlisted" : "Wishlist"}
                </button>
                {property.whatsapp_link ? (
                  <a className="crm-secondary-btn" href={property.whatsapp_link} target="_blank" rel="noreferrer">
                    WhatsApp
                  </a>
                ) : null}
                <button className="crm-primary-btn" type="button" onClick={() => onScheduleVisit(property)}>
                  {roleGroup === "customer" ? "Schedule Visit" : "Create Visit"}
                </button>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function ListingsBoard({ properties, roleGroup, onApprove, onReject }) {
  return (
    <SectionCard title="Listings Control" subtitle="Monitor inventory quality, approvals, and agent ownership.">
      {properties.length ? (
        <div className="crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <th>Listing</th>
                <th>Type</th>
                <th>Area</th>
                <th>Owner / Agent</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {properties.map((property) => (
                <tr key={property.id}>
                  <td>
                    <strong>{property.title}</strong>
                    <small>{property.city}, {property.state || "-"}</small>
                  </td>
                  <td>
                    <strong>{property.property_type}</strong>
                    <small>{property.listing_type}</small>
                  </td>
                  <td>
                    <strong>{property.area_sqft || "-"}</strong>
                    <small>{property.bedrooms || 0} bed / {property.bathrooms || 0} bath</small>
                  </td>
                  <td>
                    <strong>{property.assigned_agent_name || "Direct Owner"}</strong>
                    <small>{property.owner || "-"}</small>
                  </td>
                  <td>
                    <span className={badgeTone(property.status)}>{property.status}</span>
                  </td>
                  <td>
                    {roleGroup === "admin" ? (
                      <div className="crm-inline-actions">
                        <button className="crm-secondary-btn" type="button" onClick={() => onApprove(property.id)}>
                          Approve
                        </button>
                        <button className="crm-secondary-btn crm-danger-btn" type="button" onClick={() => onReject(property.id)}>
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="crm-muted-text">Agent visibility only</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="crm-empty-state">No listings uploaded yet.</div>
      )}
    </SectionCard>
  );
}

function WalletPanel({ wallet, transactions, withdraws, withdrawAmount, setWithdrawAmount, onWithdraw }) {
  return (
    <div className="crm-grid-2">
      <SectionCard title="Wallet" subtitle="Track credits, debits, and cash-out requests.">
        <div className="crm-wallet-highlight">
          <div>
            <span>Available Balance</span>
            <strong>{formatCurrency(wallet?.balance || 0)}</strong>
          </div>
          <div>
            <span>Currency</span>
            <strong>{wallet?.currency || "INR"}</strong>
          </div>
        </div>
        <div className="crm-inline-actions crm-top-gap">
          <input
            type="number"
            min="1"
            placeholder="Withdrawal amount"
            value={withdrawAmount}
            onChange={(event) => setWithdrawAmount(event.target.value)}
          />
          <button className="crm-primary-btn" type="button" onClick={onWithdraw}>
            Request Withdrawal
          </button>
        </div>
        <div className="crm-mini-list crm-top-gap">
          {withdraws.length ? (
            withdraws.map((withdraw) => (
              <div key={withdraw.id} className="crm-mini-item">
                <div>
                  <strong>{formatCurrency(withdraw.amount)}</strong>
                  <small>{formatDateTime(withdraw.requested_at)}</small>
                </div>
                <span className={badgeTone(withdraw.status)}>{withdraw.status}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">No withdrawal requests yet.</div>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Wallet Ledger" subtitle="Latest transaction history for leads, commissions, and adjustments.">
        <div className="crm-mini-list">
          {transactions.length ? (
            transactions.slice(0, 12).map((transaction) => (
              <div key={transaction.id} className="crm-mini-item">
                <div>
                  <strong>{formatCurrency(transaction.amount)}</strong>
                  <small>{transaction.source || transaction.entry_type}</small>
                </div>
                <span className={badgeTone(transaction.entry_type)}>{transaction.entry_type}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">No wallet activity yet.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function PackagesPanel({ plans, subscriptions, roleGroup, onSelectPlan, onActivateFreePlan }) {
  const current = subscriptions[0];

  return (
    <SectionCard
      title="Packages"
      subtitle="Configure SaaS access for lead volume, listing limits, CRM tooling, and analytics."
      action={
        roleGroup !== "customer" ? (
          <button className="crm-secondary-btn" type="button" onClick={onActivateFreePlan}>
            Activate Free Plan
          </button>
        ) : null
      }
    >
      <div className="crm-plan-grid">
        {plans.map((plan) => {
          const active = current?.plan === plan.id;
          return (
            <article key={plan.id} className={`crm-plan-card ${active ? "active" : ""}`}>
              <div className="crm-plan-top">
                <div>
                  <span className="crm-kicker">{plan.slug || "plan"}</span>
                  <h3>{plan.name}</h3>
                </div>
                <strong>{formatCurrency(plan.price_monthly || plan.price || 0)}</strong>
              </div>
              <p>{plan.description || "Built for scaling teams that need stronger distribution and automation controls."}</p>
              <ul>
                <li>{plan.max_leads_per_month} leads / month</li>
                <li>{plan.max_property_listings} listings</li>
                <li>{plan.crm_access ? "CRM tools enabled" : "CRM tools disabled"}</li>
                <li>{plan.marketing_tools_access ? "Marketing suite enabled" : "Marketing suite disabled"}</li>
                <li>{plan.analytics_access ? "Analytics unlocked" : "Analytics basic only"}</li>
              </ul>
              <button className="crm-primary-btn" type="button" onClick={() => onSelectPlan(plan.id)} disabled={active}>
                {active ? "Current Plan" : "Choose Plan"}
              </button>
            </article>
          );
        })}
      </div>
    </SectionCard>
  );
}

function MessagesPanel({ notifications, calls, voiceCalls, onMarkAllRead }) {
  return (
    <div className="crm-grid-2">
      <SectionCard title="Notifications" subtitle="Unread alerts, lead updates, and system nudges." action={<button className="crm-secondary-btn" type="button" onClick={onMarkAllRead}>Mark all read</button>}>
        <div className="crm-mini-list">
          {notifications.length ? (
            notifications.slice(0, 12).map((notification) => (
              <div key={notification.id} className="crm-mini-item">
                <div>
                  <strong>{notification.title || notification.level}</strong>
                  <small>{notification.body || "Platform notification"}</small>
                </div>
                <span className={badgeTone(notification.level)}>{notification.read_at ? "Read" : "Unread"}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">No notifications right now.</div>
          )}
        </div>
      </SectionCard>
      <SectionCard title="Call Activity" subtitle="Recent telephony logs linked to customer and lead records.">
        <div className="crm-mini-list">
          {calls.length ? (
            calls.slice(0, 12).map((call) => (
              <div key={call.id} className="crm-mini-item">
                <div>
                  <strong>{call.lead_name || call.phone_number || "Call log"}</strong>
                  <small>{call.outcome || call.direction}</small>
                </div>
                <span className={badgeTone(call.missed_call ? "danger" : "info")}>{call.missed_call ? "Missed" : `${call.duration_seconds || 0}s`}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">No call logs yet.</div>
          )}
        </div>
      </SectionCard>
      <SectionCard title="AI Voice Qualification" subtitle="Lead qualification calls and transcript-ready automation activity.">
        <div className="crm-mini-list">
          {voiceCalls.length ? (
            voiceCalls.slice(0, 12).map((call) => (
              <div key={call.id} className="crm-mini-item">
                <div>
                  <strong>{call.lead_name || call.lead_display || "Voice qualification"}</strong>
                  <small>{call.qualification_status || call.trigger || "AI conversation"}</small>
                </div>
                <span className={badgeTone(call.qualification_status || "pending")}>{call.language || "auto"}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">AI voice logs will appear here once qualification calls begin.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function AnalyticsPanel({ dashboard, summary, assignments, builders, projects, intelligenceDashboard, aggregatedProperties, heatmaps, priceTrends, investorMatches, premiumLeads }) {
  const statusBreakdown = dashboard?.status_breakdown || [];
  const sourceBreakdown = dashboard?.source_breakdown || [];
  const assignmentRows = assignments.slice(0, 8);
  const topAreas = intelligenceDashboard?.top_investment_areas || [];
  const topAgents = intelligenceDashboard?.top_agents || [];

  return (
    <div className="crm-grid-2">
      <SectionCard title="Performance Radar" subtitle="Real-time lead conversion and source quality overview.">
        <div className="crm-metric-stack">
          <div className="crm-metric-bar">
            <span>Conversion Rate</span>
            <strong>{dashboard?.conversion_rate || 0}%</strong>
          </div>
          {statusBreakdown.map((row) => (
            <div className="crm-progress-row" key={`status-${row.status}`}>
              <span>{row.status}</span>
              <div><i style={{ width: `${Math.max(8, row.count * 10)}px` }} /></div>
              <strong>{row.count}</strong>
            </div>
          ))}
          {!statusBreakdown.length ? <div className="crm-empty-state slim">Lead stages will appear here once traffic starts moving.</div> : null}
        </div>
      </SectionCard>

      <SectionCard title="Channel Mix" subtitle="Compare ad, web, and referral volume against listings and builder supply.">
        <div className="crm-metric-stack">
          {sourceBreakdown.map((row) => (
            <div className="crm-progress-row" key={`source-${row.source}`}>
              <span>{row.source}</span>
              <div><i style={{ width: `${Math.max(8, row.count * 12)}px` }} /></div>
              <strong>{row.count}</strong>
            </div>
          ))}
          <div className="crm-summary-band">
            <div>
              <span>Builders</span>
              <strong>{builders.length}</strong>
            </div>
            <div>
              <span>Projects</span>
              <strong>{projects.length}</strong>
            </div>
            <div>
              <span>Revenue</span>
              <strong>{formatCurrency(summary?.revenue)}</strong>
            </div>
            <div>
              <span>Aggregated Properties</span>
              <strong>{aggregatedProperties.length}</strong>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Assignment Trail" subtitle="Latest auto-routing and reassignment decisions.">
        <div className="crm-mini-list">
          {assignmentRows.length ? (
            assignmentRows.map((item) => (
              <div key={item.id} className="crm-mini-item">
                <div>
                  <strong>{item.agent_name || "Unassigned"}</strong>
                  <small>{item.note || item.matched_on}</small>
                </div>
                <span className={badgeTone(item.assignment_type)}>{item.assignment_type}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">Assignment history will appear after routing starts.</div>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Market Intelligence" subtitle="Demand, trend, and opportunity cards from the intelligence backend.">
        <div className="crm-mini-list">
          <div className="crm-mini-item">
            <div>
              <strong>Demand heatmaps</strong>
              <small>{heatmaps.length ? "City and district demand clusters are available." : "Heatmap engine ready. Add search/view activity to generate clusters."}</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{heatmaps.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Price trend snapshots</strong>
              <small>{priceTrends.length ? "Historical price movement is being tracked." : "Trend snapshots will appear once location history is built."}</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{priceTrends.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Investor matches</strong>
              <small>{investorMatches.length ? "ROI and fit-based matches are available for properties and builder launches." : "Investor engine ready for projects and high-ROI inventory."}</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{investorMatches.length}</span>
          </div>
          <div className="crm-mini-item">
            <div>
              <strong>Premium leads</strong>
              <small>Hot, exclusive, and verified lead inventory visible to the platform.</small>
            </div>
            <span className="crm-badge crm-badge-neutral">{premiumLeads.length}</span>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Top Investment Areas" subtitle="Locations currently surfacing in the intelligence dashboard.">
        <div className="crm-mini-list">
          {topAreas.length ? (
            topAreas.map((area, index) => (
              <div key={`${area.city}-${area.district}-${index}`} className="crm-mini-item">
                <div>
                  <strong>{area.city || area.district || "Emerging locality"}</strong>
                  <small>{`Demand ${area.demand_score || 0} • Low supply ${area.low_supply_score || 0}`}</small>
                </div>
                <span className="crm-badge crm-badge-neutral">{area.hot_investment_score || 0}</span>
              </div>
            ))
          ) : (
            <div className="crm-empty-state slim">Top investment zones will appear after demand and pricing snapshots are generated.</div>
          )}
        </div>
        {topAgents.length ? (
          <div className="crm-mini-list crm-top-gap">
            {topAgents.map((agent, index) => (
              <div key={`${agent.assigned_agent__name || "agent"}-${index}`} className="crm-mini-item">
                <div>
                  <strong>{agent.assigned_agent__name || "Closed deal agent"}</strong>
                  <small>{`${agent.closed || 0} closed deals in intelligence snapshot`}</small>
                </div>
                <span className="crm-badge crm-badge-neutral">{formatCurrency(agent.revenue || 0)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

function AgentsPanel({ agents }) {
  return (
    <SectionCard title="Agent Network" subtitle="Coverage, approvals, franchise structure, and wallet visibility.">
      {agents.length ? (
        <div className="crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Coverage</th>
                <th>Approval</th>
                <th>Wallet</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>
                    <strong>{agent.name || agent.user_email}</strong>
                    <small>{agent.franchise_name || agent.user_role || "-"}</small>
                  </td>
                  <td>
                    <strong>{agent.city || "-"}</strong>
                    <small>{[agent.district, agent.state, agent.pin_code].filter(Boolean).join(", ") || "Not mapped"}</small>
                  </td>
                  <td>
                    <span className={badgeTone(agent.approval_status)}>{agent.approval_status}</span>
                  </td>
                  <td>{formatCurrency(agent.wallet_balance)}</td>
                  <td>
                    <strong>{formatCompactNumber(agent.total_sales)}</strong>
                    <small>{agent.total_visits || 0} visits</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="crm-empty-state">No agent profiles are visible yet.</div>
      )}
    </SectionCard>
  );
}

function VisitsPanel({ visits }) {
  return (
    <SectionCard title="Scheduled Visits" subtitle="Customer walkthroughs, field activity, and visit completion status.">
      <div className="crm-mini-list">
        {visits.length ? (
          visits.map((visit) => (
            <div key={visit.id} className="crm-mini-item">
              <div>
                <strong>{visit.lead_name || "Lead visit"}</strong>
                <small>{formatDateTime(visit.visit_date)} • {visit.location || "-"}</small>
              </div>
              <span className={badgeTone(visit.status)}>{visit.status}</span>
            </div>
          ))
        ) : (
          <div className="crm-empty-state slim">No property visits scheduled yet.</div>
        )}
      </div>
    </SectionCard>
  );
}

function CompareTray({ properties }) {
  if (!properties.length) return null;
  return (
    <SectionCard title="Compare Properties" subtitle="Quick side-by-side shortlist for price, space, and fit.">
      <div className="crm-compare-grid">
        {properties.map((property) => (
          <div key={property.id} className="crm-compare-card">
            <strong>{property.title}</strong>
            <small>{property.city}, {property.state || "-"}</small>
            <ul>
              <li>{formatCurrency(property.price)}</li>
              <li>{property.area_sqft || "-"} sqft</li>
              <li>{property.bedrooms || 0} bed / {property.bathrooms || 0} bath</li>
              <li>{property.furnishing || "unfurnished"}</li>
            </ul>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export default function RealEstateWorkspace({ viewport = "desktop", modeLabel = "DESKTOP" }) {
  const [session, setSession] = useState(Api.getSession());
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [loginBusy, setLoginBusy] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [loading, setLoading] = useState(Boolean(session.accessToken));
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [me, setMe] = useState(null);
  const [summary, setSummary] = useState({});
  const [dashboard, setDashboard] = useState({});
  const [leads, setLeads] = useState([]);
  const [properties, setProperties] = useState([]);
  const [wishlist, setWishlist] = useState([]);
  const [agents, setAgents] = useState([]);
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [withdraws, setWithdraws] = useState([]);
  const [plans, setPlans] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [visits, setVisits] = useState([]);
  const [calls, setCalls] = useState([]);
  const [voiceCalls, setVoiceCalls] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [builders, setBuilders] = useState([]);
  const [projects, setProjects] = useState([]);
  const [intelligenceDashboard, setIntelligenceDashboard] = useState({});
  const [aggregatedProperties, setAggregatedProperties] = useState([]);
  const [heatmaps, setHeatmaps] = useState([]);
  const [priceTrends, setPriceTrends] = useState([]);
  const [investorMatches, setInvestorMatches] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [premiumLeads, setPremiumLeads] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [leadMonitoring, setLeadMonitoring] = useState({});
  const [leadKanban, setLeadKanban] = useState([]);
  const [leadSources, setLeadSources] = useState([]);
  const [importBatches, setImportBatches] = useState([]);
  const [currentAssignments, setCurrentAssignments] = useState([]);
  const [deals, setDeals] = useState([]);
  const [dealPayments, setDealPayments] = useState([]);
  const [agentDashboard, setAgentDashboard] = useState(null);
  const [customerDashboard, setCustomerDashboard] = useState(null);
  const [activeView, setActiveView] = useState("dashboard");
  const [leadForm, setLeadForm] = useState({
    name: "",
    phone: "",
    email: "",
    budget: "",
    property_type: "",
    city: "",
    district: "",
    state: "",
    pincode: "",
    source: "website",
    notes: "",
  });
  const [propertyForm, setPropertyForm] = useState({
    title: "",
    price: "",
    listing_type: "sale",
    property_type: "house",
    area_sqft: "",
    bedrooms: "",
    bathrooms: "",
    furnishing: "unfurnished",
    city: "",
    district: "",
    state: "",
    pin_code: "",
    location: "",
    description: "",
  });
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [leadSearch, setLeadSearch] = useState("");
  const [propertySearch, setPropertySearch] = useState("");
  const [compareIds, setCompareIds] = useState([]);
  const [leadActivities, setLeadActivities] = useState([]);
  const [comparePropertiesData, setComparePropertiesData] = useState([]);
  const [selectedLeadIds, setSelectedLeadIds] = useState([]);
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [leadTimeline, setLeadTimeline] = useState([]);
  const [bulkAgentId, setBulkAgentId] = useState("");
  const [bulkAutoAssign, setBulkAutoAssign] = useState(false);
  const [csvImportFile, setCsvImportFile] = useState(null);

  const deferredLeadSearch = useDeferredValue(leadSearch);
  const deferredPropertySearch = useDeferredValue(propertySearch);
  const roleGroup = resolveRoleGroup(me);
  const navItems = NAV_ITEMS[roleGroup] || NAV_ITEMS.customer;
  const navLabel = NAV_LABELS[activeView] || "Workspace";
  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";

  useEffect(() => {
    if (!message && !error) return undefined;
    const timer = window.setTimeout(() => {
      setMessage("");
      setError("");
    }, 3500);
    return () => window.clearTimeout(timer);
  }, [message, error]);

  useEffect(() => {
    if (!navItems.includes(activeView)) {
      setActiveView(navItems[0]);
    }
  }, [activeView, navItems]);

  function resetWorkspace() {
    startTransition(() => {
      setMe(null);
      setSummary({});
      setDashboard({});
      setLeads([]);
      setProperties([]);
      setWishlist([]);
      setAgents([]);
      setWallet(null);
      setTransactions([]);
      setWithdraws([]);
      setPlans([]);
      setSubscriptions([]);
      setNotifications([]);
      setVisits([]);
      setCalls([]);
      setVoiceCalls([]);
      setAssignments([]);
      setBuilders([]);
      setProjects([]);
      setIntelligenceDashboard({});
      setAggregatedProperties([]);
      setHeatmaps([]);
      setPriceTrends([]);
      setInvestorMatches([]);
      setAlerts([]);
      setPremiumLeads([]);
      setDocuments([]);
      setLeadMonitoring({});
      setLeadKanban([]);
      setLeadSources([]);
      setImportBatches([]);
      setCurrentAssignments([]);
      setDeals([]);
      setDealPayments([]);
      setAgentDashboard(null);
      setCustomerDashboard(null);
      setLeadActivities([]);
      setLeadTimeline([]);
      setComparePropertiesData([]);
      setCompareIds([]);
      setSelectedLeadIds([]);
      setSelectedLeadId(null);
      setBulkAgentId("");
      setBulkAutoAssign(false);
      setCsvImportFile(null);
      setActiveView("dashboard");
    });
  }

  function setFlash(nextMessage = "", nextError = "") {
    setMessage(nextMessage);
    setError(nextError);
  }

  function handleLogout(nextMessage = "Signed out.") {
    Api.clearSession();
    setSession(Api.getSession());
    setLoginError("");
    setLoading(false);
    setRefreshing(false);
    resetWorkspace();
    setFlash(nextMessage, "");
  }

  async function loadWorkspace({ soft = false } = {}) {
    if (!session.accessToken) {
      setLoading(false);
      return;
    }

    if (soft) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError("");

    const requests = await Promise.allSettled([
      Api.fetchMe(),
      Api.fetchSummaryReport(),
      Api.fetchLeadDashboard(),
      Api.fetchLeadMonitoring(),
      Api.fetchLeadKanban(),
      Api.fetchLeads(),
      Api.fetchProperties(),
      Api.fetchWishlist(),
      Api.fetchAgents(),
      Api.fetchAgentDashboard(),
      Api.fetchCustomersDashboard(),
      Api.fetchWallets(),
      Api.fetchWalletTransactions(),
      Api.fetchWithdrawRequests(),
      Api.fetchPlans(),
      Api.fetchSubscriptions(),
      Api.fetchNotifications(),
      Api.fetchVisits(),
      Api.fetchCalls(),
      Api.fetchVoiceCalls(),
      Api.fetchCurrentAssignments(),
      Api.fetchLeadAssignments(),
      Api.fetchLeadSources(),
      Api.fetchLeadImportBatches(),
      Api.fetchDeals(),
      Api.fetchDealPayments(),
      Api.fetchBuilders(),
      Api.fetchProjects(),
      Api.fetchLeadActivities(),
      Api.fetchIntelligenceDashboard(),
      Api.fetchAggregatedProperties(),
      Api.fetchHeatmaps(),
      Api.fetchPriceTrends(),
      Api.fetchInvestorMatches(),
      Api.fetchAlerts(),
      Api.fetchPremiumLeads(),
      Api.fetchDocuments(),
    ]);

    const [meRes, summaryRes, dashboardRes, monitoringRes, kanbanRes, leadsRes, propertiesRes, wishlistRes, agentsRes, agentDashboardRes, customerDashboardRes, walletsRes, transactionsRes, withdrawsRes, plansRes, subscriptionsRes, notificationsRes, visitsRes, callsRes, voiceCallsRes, currentAssignmentsRes, assignmentsRes, sourcesRes, importBatchesRes, dealsRes, dealPaymentsRes, buildersRes, projectsRes, activitiesRes, intelligenceDashboardRes, aggregatedPropertiesRes, heatmapsRes, priceTrendsRes, investorMatchesRes, alertsRes, premiumLeadsRes, documentsRes] =
      requests;

    if (meRes.status !== "fulfilled") {
      if (meRes.reason?.status === 401) {
        handleLogout("Session expired. Please sign in again.");
        return;
      }
      setFlash("", meRes.reason?.message || "Unable to load your workspace profile.");
      setLoading(false);
      setRefreshing(false);
      return;
    }

    const valueOf = (result, fallback) => (result.status === "fulfilled" ? result.value : fallback);
    const nextWallets = normalizeList(valueOf(walletsRes, []));

    startTransition(() => {
      setMe(meRes.value || null);
      setSummary(valueOf(summaryRes, {}) || {});
      setDashboard(valueOf(dashboardRes, {}) || {});
      setLeadMonitoring(valueOf(monitoringRes, {}) || {});
      setLeadKanban(normalizeList(valueOf(kanbanRes, [])));
      setLeads(normalizeList(valueOf(leadsRes, [])));
      setProperties(normalizeList(valueOf(propertiesRes, [])));
      setWishlist(normalizeList(valueOf(wishlistRes, [])));
      setAgents(normalizeList(valueOf(agentsRes, [])));
      setAgentDashboard(valueOf(agentDashboardRes, null));
      setCustomerDashboard(valueOf(customerDashboardRes, null));
      setWallet(nextWallets[0] || null);
      setTransactions(normalizeList(valueOf(transactionsRes, [])));
      setWithdraws(normalizeList(valueOf(withdrawsRes, [])));
      setPlans(normalizeList(valueOf(plansRes, [])));
      setSubscriptions(normalizeList(valueOf(subscriptionsRes, [])));
      setNotifications(normalizeList(valueOf(notificationsRes, [])));
      setVisits(normalizeList(valueOf(visitsRes, [])));
      setCalls(normalizeList(valueOf(callsRes, [])));
      setVoiceCalls(normalizeList(valueOf(voiceCallsRes, [])));
      setCurrentAssignments(normalizeList(valueOf(currentAssignmentsRes, [])));
      setAssignments(normalizeList(valueOf(assignmentsRes, [])));
      setLeadSources(normalizeList(valueOf(sourcesRes, [])));
      setImportBatches(normalizeList(valueOf(importBatchesRes, [])));
      setDeals(normalizeList(valueOf(dealsRes, [])));
      setDealPayments(normalizeList(valueOf(dealPaymentsRes, [])));
      setBuilders(normalizeList(valueOf(buildersRes, [])));
      setProjects(normalizeList(valueOf(projectsRes, [])));
      setIntelligenceDashboard(valueOf(intelligenceDashboardRes, {}) || {});
      setAggregatedProperties(normalizeList(valueOf(aggregatedPropertiesRes, [])));
      setHeatmaps(normalizeList(valueOf(heatmapsRes, [])));
      setPriceTrends(normalizeList(valueOf(priceTrendsRes, [])));
      setInvestorMatches(normalizeList(valueOf(investorMatchesRes, [])));
      setAlerts(normalizeList(valueOf(alertsRes, [])));
      setPremiumLeads(normalizeList(valueOf(premiumLeadsRes, [])));
      setDocuments(normalizeList(valueOf(documentsRes, [])));
      setLeadActivities(normalizeList(valueOf(activitiesRes, [])));
    });

    if (soft) {
      setFlash("Workspace refreshed.", "");
    }

    setLoading(false);
    setRefreshing(false);
  }

  useEffect(() => {
    if (!session.accessToken) {
      setLoading(false);
      resetWorkspace();
      return;
    }
    loadWorkspace();
  }, [session.accessToken]);

  useEffect(() => {
    if (!session.accessToken || compareIds.length < 2) {
      setComparePropertiesData([]);
      return;
    }

    let cancelled = false;

    Api.compareProperties(compareIds)
      .then((payload) => {
        if (!cancelled) {
          setComparePropertiesData(normalizeList(payload));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setComparePropertiesData(properties.filter((item) => compareIds.includes(item.id)));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [compareIds, properties, session.accessToken]);

  useEffect(() => {
    if (!session.accessToken || !selectedLeadId) {
      setLeadTimeline([]);
      return;
    }
    let cancelled = false;
    Api.fetchLeadTimeline(selectedLeadId)
      .then((payload) => {
        if (!cancelled) {
          setLeadTimeline(normalizeList(payload));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLeadTimeline([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedLeadId, session.accessToken]);

  async function handleLogin(event) {
    event.preventDefault();
    setLoginBusy(true);
    setLoginError("");
    try {
      const tokens = await Api.login({
        email: loginForm.email,
        password: loginForm.password,
      });
      Api.setSession(tokens);
      setSession(Api.getSession());
      setFlash("Welcome back.", "");
    } catch (requestError) {
      setLoginError(requestError.message || "Unable to sign in.");
    } finally {
      setLoginBusy(false);
    }
  }

  function handleUseDemoUser(user) {
    setLoginForm({ email: user.email, password: user.password });
    setLoginError("");
    setMessage(`${user.label} credentials filled. Click Enter Workspace.`);
  }

  async function handleLeadSubmit(event) {
    event.preventDefault();
    try {
      await Api.createLead({
        name: leadForm.name,
        phone: leadForm.phone,
        email: leadForm.email,
        budget: leadForm.budget || undefined,
        property_type: leadForm.property_type,
        preferred_location: leadForm.city,
        city: leadForm.city,
        district: leadForm.district,
        state: leadForm.state,
        pincode_text: leadForm.pincode,
        source: leadForm.source,
        notes: leadForm.notes,
      });
      setLeadForm({
        name: "",
        phone: "",
        email: "",
        budget: "",
        property_type: "",
        city: "",
        district: "",
        state: "",
        pincode: "",
        source: "website",
        notes: "",
      });
      setActiveView(roleGroup === "customer" ? "deals" : "leads");
      setFlash("Lead captured and routed.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Lead could not be created.");
    }
  }

  async function handleStatusChange(lead, nextStatus) {
    if (!nextStatus) return;
    const stageMap = {
      new: "new",
      contacted: "contacted",
      in_progress: "follow_up",
      qualified: "qualified",
      closed: "deal_closed",
      lost: "lost_lead",
    };
    try {
      await Api.updateLeadStatus(lead.id, {
        status: nextStatus,
        stage: stageMap[nextStatus],
        note: `Updated from ${modeLabel} workspace`,
      });
      setFlash(`Lead ${lead.name || lead.mobile || lead.id} updated.`, "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Lead status update failed.");
    }
  }

  async function handleAssignLead(lead, agentId) {
    if (!agentId) return;
    try {
      await Api.assignLead(lead.id, agentId);
      setFlash(`Lead reassigned for ${lead.name || lead.mobile || lead.id}.`, "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Lead reassignment failed.");
    }
  }

  async function handleLogCall(lead) {
    const note = window.prompt("Add a quick call note", `Spoke with ${lead.name || "lead"} about the property search.`);
    if (note === null) return;
    try {
      await Api.logLeadCall(lead.id, {
        direction: "outbound",
        duration_seconds: 120,
        outcome: "contacted",
        note,
        missed_call: false,
        telephony_provider: "manual_click_to_call",
      });
      setFlash("Call log saved to CRM history.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Call log could not be saved.");
    }
  }

  function handleToggleLeadSelection(leadId) {
    setSelectedLeadIds((prev) => (prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]));
  }

  function handleSelectAllVisibleLeads() {
    if (selectedLeadIds.length === filteredLeads.length) {
      setSelectedLeadIds([]);
      return;
    }
    setSelectedLeadIds(filteredLeads.map((lead) => lead.id));
  }

  async function handleBulkAssign() {
    if (!selectedLeadIds.length) {
      setFlash("", "Select at least one lead first.");
      return;
    }
    try {
      await Api.bulkAssignLeads({
        lead_ids: selectedLeadIds,
        agent: bulkAutoAssign ? undefined : Number(bulkAgentId || 0) || undefined,
        auto: bulkAutoAssign,
        reason: bulkAutoAssign ? "Auto rebalance from workspace" : "Bulk assignment from workspace",
      });
      setSelectedLeadIds([]);
      setBulkAgentId("");
      setBulkAutoAssign(false);
      setFlash("Bulk assignment completed.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Bulk assignment failed.");
    }
  }

  async function handleCsvImport(event) {
    event.preventDefault();
    if (!csvImportFile) {
      setFlash("", "Choose a CSV file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", csvImportFile);
    formData.append("source", "Workspace CSV");
    formData.append("auto_assign", "true");
    try {
      await Api.importLeadsCsv(formData);
      setCsvImportFile(null);
      setFlash("CSV import queued and processed.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "CSV import failed.");
    }
  }

  async function handleConvertLead(lead) {
    const dealAmount = window.prompt("Deal amount", String(lead.deal_value || lead.budget || ""));
    if (dealAmount === null) return;
    try {
      await Api.convertLead(lead.id, {
        deal_amount: dealAmount,
        customer_name: lead.name,
        customer_email: lead.email,
        customer_phone: lead.mobile,
      });
      setFlash("Lead converted. Deal and commission created.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Lead conversion failed.");
    }
  }

  async function handleLeadContact(lead, channel) {
    const messageText = window.prompt(`Message for ${channel}`, `Hi ${lead.name || "there"}, sharing an update on your property inquiry.`);
    if (messageText === null) return;
    try {
      await Api.contactLead(lead.id, { channel, message: messageText });
      setFlash(`${channel} activity logged.`, "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Contact log failed.");
    }
  }

  async function handlePropertySubmit(event) {
    event.preventDefault();
    try {
      await Api.createProperty({
        title: propertyForm.title,
        price: propertyForm.price,
        listing_type: propertyForm.listing_type,
        property_type: propertyForm.property_type,
        area_sqft: propertyForm.area_sqft || undefined,
        bedrooms: propertyForm.bedrooms || undefined,
        bathrooms: propertyForm.bathrooms || undefined,
        furnishing: propertyForm.furnishing,
        city: propertyForm.city,
        district: propertyForm.district,
        state: propertyForm.state,
        pin_code: propertyForm.pin_code,
        location: propertyForm.location,
        description: propertyForm.description,
        status: roleGroup === "admin" ? "approved" : "pending_approval",
      });
      setPropertyForm({
        title: "",
        price: "",
        listing_type: "sale",
        property_type: "house",
        area_sqft: "",
        bedrooms: "",
        bathrooms: "",
        furnishing: "unfurnished",
        city: "",
        district: "",
        state: "",
        pin_code: "",
        location: "",
        description: "",
      });
      setActiveView("properties");
      setFlash("Property submitted to the marketplace.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Property could not be published.");
    }
  }

  function handleToggleCompare(propertyId) {
    setCompareIds((prev) => {
      if (prev.includes(propertyId)) {
        return prev.filter((id) => id !== propertyId);
      }
      if (prev.length >= 3) {
        setFlash("", "Compare tray supports up to 3 properties at a time.");
        return prev;
      }
      return [...prev, propertyId];
    });
  }

  async function handleToggleWishlist(propertyId) {
    try {
      await Api.toggleWishlist(propertyId);
      setFlash("Wishlist updated.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Wishlist could not be updated.");
    }
  }

  async function handleScheduleVisit(property) {
    const note = window.prompt("Visit note", `Interested in ${property.title} and would like a guided site visit.`);
    if (note === null) return;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(11, 0, 0, 0);
    try {
      await Api.scheduleVisit(property.id, {
        visit_date: tomorrow.toISOString(),
        notes: note,
      });
      setActiveView("deals");
      setFlash("Visit scheduled and linked to the CRM.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Visit could not be scheduled.");
    }
  }

  async function handleApproveProperty(propertyId) {
    try {
      await Api.approveProperty(propertyId);
      setFlash("Listing approved.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Listing approval failed.");
    }
  }

  async function handleRejectProperty(propertyId) {
    try {
      await Api.rejectProperty(propertyId);
      setFlash("Listing rejected.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Listing rejection failed.");
    }
  }

  async function handleWithdraw() {
    if (!withdrawAmount) return;
    try {
      await Api.createWithdrawRequest({ amount: withdrawAmount });
      setWithdrawAmount("");
      setFlash("Withdrawal request sent for review.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Withdrawal request failed.");
    }
  }

  async function handleSelectPlan(planId) {
    try {
      await Api.subscribeToPlan(planId);
      setFlash("Subscription updated.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Plan selection failed.");
    }
  }

  async function handleActivateFreePlan() {
    try {
      await Api.activateFreePlan();
      setFlash("Free plan activated.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Free plan activation failed.");
    }
  }

  async function handleMarkAllRead() {
    try {
      await Api.markAllNotificationsRead();
      setFlash("Notifications marked as read.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Notifications could not be updated.");
    }
  }

  async function handleApprovePayment(paymentId) {
    try {
      await Api.approveDealPayment(paymentId);
      setFlash("Payment approved.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Payment approval failed.");
    }
  }

  async function handleMarkPaymentPaid(paymentId) {
    try {
      await Api.markDealPaymentPaid(paymentId);
      setFlash("Payment marked as paid.", "");
      await loadWorkspace({ soft: true });
    } catch (requestError) {
      setFlash("", requestError.message || "Payment update failed.");
    }
  }

  const filteredLeads = leads.filter((lead) => {
    const query = deferredLeadSearch.trim().toLowerCase();
    if (!query) return true;
    const haystack = [
      lead.name,
      lead.mobile,
      lead.email,
      lead.city,
      lead.district,
      lead.state,
      lead.status,
      lead.source,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });

  const filteredProperties = properties.filter((property) => {
    const query = deferredPropertySearch.trim().toLowerCase();
    if (!query) return true;
    const haystack = [
      property.title,
      property.description,
      property.city,
      property.location,
      property.district,
      property.state,
      property.property_type,
      property.listing_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });

  const wishlistProperties = wishlist
    .map((entry) => entry.property_detail || entry.property || entry)
    .filter(Boolean);

  const compareProperties = comparePropertiesData.length
    ? comparePropertiesData
    : properties.filter((property) => compareIds.includes(property.id));

  const statItems = [
    {
      label: roleGroup === "customer" ? "Wishlist" : "Lead Volume",
      value: formatCompactNumber(roleGroup === "customer" ? wishlistProperties.length : dashboard?.total_leads || summary?.leads_total || leads.length),
      caption: roleGroup === "customer" ? "Saved shortlist and favorites" : "Across campaigns and direct capture",
    },
    {
      label: "Listings",
      value: formatCompactNumber(filteredProperties.length),
      caption: `${filteredProperties.filter((item) => item.status === "approved" || item.status === "active").length} live in marketplace`,
    },
    {
      label: "Visits",
      value: formatCompactNumber(visits.length || dashboard?.site_visits || 0),
      caption: "Upcoming and completed field activity",
    },
    {
      label: roleGroup === "customer" ? "Budget Match" : "Revenue",
      value: roleGroup === "customer" ? formatCurrency(filteredProperties[0]?.price || 0) : formatCurrency(summary?.revenue || dashboard?.total_revenue || 0),
      caption: roleGroup === "customer" ? "Closest property from current inventory" : "Closed deals and payouts",
    },
    {
      label: "Wallet",
      value: formatCurrency(wallet?.balance || me?.wallet_balance || 0),
      caption: "Credits, commissions, and payouts",
    },
    {
      label: "Conversion",
      value: `${dashboard?.conversion_rate || 0}%`,
      caption: "Lead to closure performance",
    },
  ];

  const recentLeads = filteredLeads.slice(0, 8);
  const spotlightProperties = filteredProperties.slice(0, 6);
  const recentActivities = leadActivities.slice(0, 8);
  const selectedLead = leads.find((lead) => lead.id === selectedLeadId) || null;
  const leadOverview = leadMonitoring?.total_leads ? leadMonitoring : dashboard;
  const featureTracks = ROLE_FEATURE_TRACKS[roleGroup] || ROLE_FEATURE_TRACKS.customer;
  const demoSteps = ROLE_DEMO_STEPS[roleGroup] || ROLE_DEMO_STEPS.customer;
  const settingsCards = ROLE_SETTINGS_CARDS[roleGroup] || ROLE_SETTINGS_CARDS.customer;
  const currentAgentProfile =
    agents.find((agent) => String(agent.id) === String(me?.agent_profile_id || "")) ||
    agents.find((agent) => String(agent.user_email || "").toLowerCase() === String(me?.email || "").toLowerCase()) ||
    null;
  const activeSubscription =
    subscriptions.find((entry) => String(entry.status || "").toLowerCase() === "active") ||
    subscriptions[0] ||
    null;
  const serviceGroups = [
    {
      title: "Operational Modules",
      subtitle: "Everyday modules that keep the agent network, customer journey, and marketplace moving.",
      cards: [
        {
          eyebrow: "CRM",
          title: "Lead automation",
          value: formatCompactNumber(filteredLeads.length || dashboard?.total_leads || 0),
          description: "Lead capture, routing, follow-up stages, and manual or automatic assignment from one place.",
          statusLabel: filteredLeads.length ? "Live" : "Ready",
          statusTone: filteredLeads.length ? "success" : "neutral",
          view: roleGroup === "customer" ? "services" : "leads",
          cta: roleGroup === "customer" ? "Explore CRM Stack" : "Open Leads",
        },
        {
          eyebrow: "Marketplace",
          title: "Listings + visits",
          value: formatCompactNumber(filteredProperties.length),
          description: "Property posting, approvals, comparison, wishlist, and site visit workflows.",
          statusLabel: filteredProperties.length ? "Inventory live" : "Ready",
          statusTone: filteredProperties.length ? "success" : "neutral",
          view: "marketplace",
        },
        {
          eyebrow: "Communication",
          title: "Calls + notifications",
          value: formatCompactNumber(calls.length + notifications.length + voiceCalls.length),
          description: "CRM calls, AI voice, unread alerts, and communication automation hooks for WhatsApp, SMS, and email.",
          statusLabel: calls.length || notifications.length || voiceCalls.length ? "Active" : "Ready",
          statusTone: calls.length || notifications.length || voiceCalls.length ? "warn" : "neutral",
          view: "messages",
        },
        {
          eyebrow: "Revenue",
          title: "Wallet + subscriptions",
          value: formatCurrency(wallet?.balance || me?.wallet_balance || 0),
          description: "Commissions, payouts, premium lead purchases, and plan-based operating limits.",
          statusLabel: activeSubscription ? String(activeSubscription.status || "active") : "Plan ready",
          statusTone: activeSubscription ? "success" : "neutral",
          view: "wallet",
        },
      ],
    },
    {
      title: "Intelligence Services",
      subtitle: "Advanced visibility modules that turn the CRM into a real-estate intelligence platform.",
      cards: [
        {
          eyebrow: "Aggregation",
          title: "Property data aggregation",
          value: formatCompactNumber(aggregatedProperties.length),
          description: "Imported listings with normalization, source tracking, duplicate checks, and enrichment.",
          statusLabel: aggregatedProperties.length ? "Synced" : "Ready",
          statusTone: aggregatedProperties.length ? "success" : "neutral",
          view: "analytics",
        },
        {
          eyebrow: "Demand",
          title: "Heatmaps + price trends",
          value: `${heatmaps.length} / ${priceTrends.length}`,
          description: "Demand clusters, low-supply areas, hot investment zones, and location-wise price movement.",
          statusLabel: heatmaps.length || priceTrends.length ? "Tracking" : "Ready",
          statusTone: heatmaps.length || priceTrends.length ? "warn" : "neutral",
          view: "analytics",
        },
        {
          eyebrow: "Investors",
          title: "Investor + builder engine",
          value: formatCompactNumber(investorMatches.length + projects.length + builders.length),
          description: "Investor opportunity matching, builder launches, pre-launch projects, and ROI-driven discovery.",
          statusLabel: investorMatches.length || projects.length ? "Visible" : "Ready",
          statusTone: investorMatches.length || projects.length ? "success" : "neutral",
          view: "analytics",
        },
        {
          eyebrow: "Compliance",
          title: "Documents + fraud safety",
          value: formatCompactNumber(documents.length + alerts.length + premiumLeads.length),
          description: "Secure documents, alert subscriptions, premium leads, fraud-safe review, and workflow traceability.",
          statusLabel: documents.length || alerts.length || premiumLeads.length ? "Structured" : "Ready",
          statusTone: documents.length || alerts.length || premiumLeads.length ? "warn" : "neutral",
          view: "profile",
          cta: "Open Profile Stack",
        },
      ],
    },
  ];

  function renderActiveView() {
    if (activeView === "dashboard") {
      return (
        <>
          <FeatureTrackPanel tracks={featureTracks} onJump={setActiveView} />
          <div className="crm-grid-2">
            {roleGroup === "customer" ? (
              <DealsPanel
                roleGroup={roleGroup}
                deals={deals}
                dealPayments={dealPayments}
                customerDashboard={customerDashboard}
                onApprovePayment={handleApprovePayment}
                onMarkPaymentPaid={handleMarkPaymentPaid}
              />
            ) : (
              <LeadComposer form={leadForm} setForm={setLeadForm} onSubmit={handleLeadSubmit} busy={refreshing} roleGroup={roleGroup} />
            )}
            <SectionCard
              title="Live Monitoring"
              subtitle="Track lead load, conversations, duplicates, and field execution in one place."
              action={
                <button className="crm-secondary-btn" type="button" onClick={() => setActiveView("reports")}>
                  Open Reports
                </button>
              }
            >
              <div className="crm-mini-list">
                {[
                  { label: "Total Leads", value: leadMonitoring.total_leads || dashboard.total_leads || 0, caption: "All captured enquiries" },
                  { label: "Conversion", value: `${leadMonitoring.conversion_rate || dashboard.conversion_rate || 0}%`, caption: "Converted + closed rate" },
                  { label: "Active Conversations", value: leadMonitoring.active_conversations || 0, caption: "WhatsApp, email, SMS, call logs" },
                  { label: "Duplicates", value: leadMonitoring.duplicates || 0, caption: "Detected from phone or email" },
                ].map((property) => (
                    <div className="crm-mini-item" key={property.label}>
                      <div>
                        <strong>{property.label}</strong>
                        <small>{property.caption}</small>
                      </div>
                      <span className="crm-badge crm-badge-neutral">{property.value}</span>
                    </div>
                  ))}
              </div>
            </SectionCard>
          </div>

          {roleGroup !== "customer" ? (
            <SectionCard title="Pipeline Snapshot" subtitle="Move new enquiries into visits, negotiations, and converted customers.">
              <LeadTable
                leads={recentLeads}
                agents={agents}
                roleGroup={roleGroup}
                onStatusChange={handleStatusChange}
                onAssign={handleAssignLead}
                onCallLog={handleLogCall}
                selectedIds={selectedLeadIds}
                selectedLeadId={selectedLeadId}
                onToggleSelect={handleToggleLeadSelection}
                onSelectAll={handleSelectAllVisibleLeads}
                onSelectLead={(lead) => setSelectedLeadId(lead.id)}
                onConvert={handleConvertLead}
                onContact={handleLeadContact}
              />
            </SectionCard>
          ) : null}

          {compareProperties.length ? <CompareTray properties={compareProperties} /> : null}

          <SectionCard title="Fresh Inventory" subtitle="High-visibility listings ready for brochure sharing and visit scheduling.">
            <MarketplaceGrid
              properties={spotlightProperties}
              roleGroup={roleGroup}
              compareIds={compareIds}
              onToggleCompare={handleToggleCompare}
              onToggleWishlist={handleToggleWishlist}
              onScheduleVisit={handleScheduleVisit}
            />
          </SectionCard>
        </>
      );
    }

    if (activeView === "leads") {
      return (
        <div className="crm-stack">
          <LeadComposer form={leadForm} setForm={setLeadForm} onSubmit={handleLeadSubmit} busy={refreshing} roleGroup={roleGroup} />
          <LeadOpsPanel
            agents={agents}
            selectedLeadIds={selectedLeadIds}
            bulkAgentId={bulkAgentId}
            setBulkAgentId={setBulkAgentId}
            bulkAutoAssign={bulkAutoAssign}
            setBulkAutoAssign={setBulkAutoAssign}
            onBulkAssign={handleBulkAssign}
            csvImportFile={csvImportFile}
            setCsvImportFile={setCsvImportFile}
            onCsvImport={handleCsvImport}
            importBatches={importBatches}
            leadSources={leadSources}
          />
          <KanbanBoard columns={leadKanban} onStatusChange={handleStatusChange} />
          <SectionCard title="Lead List" subtitle="Search, update stages, reassign by area, and log conversations from one table.">
            <LeadTable
              leads={filteredLeads}
              agents={agents}
              roleGroup={roleGroup}
              onStatusChange={handleStatusChange}
              onAssign={handleAssignLead}
              onCallLog={handleLogCall}
              selectedIds={selectedLeadIds}
              selectedLeadId={selectedLeadId}
              onToggleSelect={handleToggleLeadSelection}
              onSelectAll={handleSelectAllVisibleLeads}
              onSelectLead={(lead) => setSelectedLeadId(lead.id)}
              onConvert={handleConvertLead}
              onContact={handleLeadContact}
            />
          </SectionCard>
          <LeadTimelinePanel
            lead={selectedLead}
            timeline={
              leadTimeline.length
                ? leadTimeline
                : recentActivities.map((activity) => ({
                    id: activity.id,
                    title: activity.activity_type,
                    body: activity.note,
                    timestamp: activity.created_at,
                  }))
            }
          />
        </div>
      );
    }

    if (activeView === "properties") {
      return (
        <div className="crm-stack">
          {roleGroup !== "customer" ? <PropertyComposer form={propertyForm} setForm={setPropertyForm} onSubmit={handlePropertySubmit} busy={refreshing} /> : null}
          {roleGroup !== "customer" ? <ListingsBoard properties={filteredProperties} roleGroup={roleGroup} onApprove={handleApproveProperty} onReject={handleRejectProperty} /> : null}
          {compareProperties.length ? <CompareTray properties={compareProperties} /> : null}
          <SectionCard title="Property Marketplace" subtitle="Search active inventory, shortlist units, and trigger visit workflows.">
            <MarketplaceGrid
              properties={filteredProperties}
              roleGroup={roleGroup}
              compareIds={compareIds}
              onToggleCompare={handleToggleCompare}
              onToggleWishlist={handleToggleWishlist}
              onScheduleVisit={handleScheduleVisit}
            />
          </SectionCard>
        </div>
      );
    }

    if (activeView === "deals") {
      return (
        <DealsPanel
          roleGroup={roleGroup}
          deals={deals}
          dealPayments={dealPayments}
          customerDashboard={customerDashboard}
          onApprovePayment={handleApprovePayment}
          onMarkPaymentPaid={handleMarkPaymentPaid}
        />
      );
    }

    if (activeView === "agents") {
      return <AgentsPanel agents={agents} />;
    }

    if (activeView === "reports") {
      return (
        <div className="crm-stack">
          <AnalyticsPanel
            dashboard={dashboard}
            summary={summary}
            assignments={assignments}
            builders={builders}
            projects={projects}
            intelligenceDashboard={intelligenceDashboard}
            aggregatedProperties={aggregatedProperties}
            heatmaps={heatmaps}
            priceTrends={priceTrends}
            investorMatches={investorMatches}
            premiumLeads={premiumLeads}
          />
          <MessagesPanel notifications={notifications} calls={calls} voiceCalls={voiceCalls} onMarkAllRead={handleMarkAllRead} />
        </div>
      );
    }

    if (activeView === "settings") {
      return (
        <div className="crm-stack">
          <ProfilePanel
            roleGroup={roleGroup}
            me={me}
            agentProfile={currentAgentProfile}
            wallet={wallet}
            subscriptions={subscriptions}
            dashboard={dashboard}
            leads={filteredLeads}
            visits={visits}
            properties={filteredProperties}
            onJump={setActiveView}
          />
          <SettingsPanel cards={settingsCards} notifications={notifications} calls={calls} voiceCalls={voiceCalls} onJump={setActiveView} />
          {roleGroup !== "customer" ? (
            <WalletPanel
              wallet={wallet}
              transactions={transactions}
              withdraws={withdraws}
              withdrawAmount={withdrawAmount}
              setWithdrawAmount={setWithdrawAmount}
              onWithdraw={handleWithdraw}
            />
          ) : null}
          {roleGroup !== "customer" ? (
            <PackagesPanel plans={plans} subscriptions={subscriptions} roleGroup={roleGroup} onSelectPlan={handleSelectPlan} onActivateFreePlan={handleActivateFreePlan} />
          ) : null}
        </div>
      );
    }

    return (
      <SectionCard title={navLabel} subtitle="This module is ready for the next workflow extension.">
        <div className="crm-empty-state">This area is reserved for future real-estate modules like insurance, loans, and franchise operations.</div>
      </SectionCard>
    );
  }

  if (!session.accessToken) {
    return (
      <LoginPanel
        form={loginForm}
        setForm={setLoginForm}
        error={loginError}
        busy={loginBusy}
        onSubmit={handleLogin}
        onUseDemoUser={handleUseDemoUser}
        pathname={pathname}
      />
    );
  }

  if (loading) {
    return (
      <div className="crm-loading-screen">
        <div className="crm-loading-card">
          <p className="crm-kicker">Loading Workspace</p>
          <h2>Syncing CRM, marketplace, visits, wallet, and subscriptions.</h2>
          <p>Please wait while your tenant dashboard comes online.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`crm-shell crm-shell-${viewport}`}>
      <aside className="crm-sidebar">
        <div className="crm-brand-block">
          <p className="crm-kicker">PropFlow SaaS</p>
          <h2>{me?.company_name || "Real Estate Platform"}</h2>
          <span className="crm-mode-pill">{modeLabel}</span>
        </div>

        <div className="crm-user-card">
          <strong>{me?.first_name || me?.username || me?.email || "Workspace User"}</strong>
          <small>{roleGroup === "customer" ? "Buyer / Seller" : roleGroup === "agent" ? "Agent Network" : "Admin Control"}</small>
          <small>{me?.email || "No email on file"}</small>
          <small>
            {roleGroup === "agent"
              ? `Approval: ${currentAgentProfile?.approval_status || "pending"}`
              : roleGroup === "admin"
                ? `${builders.length} builders • ${projects.length} projects`
                : `${wishlistProperties.length} wishlist • ${visits.length} visits`}
          </small>
        </div>

        <nav className="crm-nav-list">
          {navItems.map((item) => (
            <button
              key={item}
              type="button"
              className={`crm-nav-btn ${activeView === item ? "active" : ""}`}
              onClick={() => setActiveView(item)}
            >
              <span>{NAV_LABELS[item]}</span>
              <small>{item.replaceAll("_", " ")}</small>
            </button>
          ))}
        </nav>

        <div className="crm-sidebar-links">
          <a href="/accounts/dashboard/">Django Dashboard</a>
          <a href="/accounts/edit-profile/">Edit Profile</a>
          <button type="button" className="crm-link-button" onClick={() => setActiveView("reports")}>
            Open Reports
          </button>
        </div>
      </aside>

      <main className="crm-main">
        <HeroPanel roleGroup={roleGroup} me={me} summary={summary} dashboard={dashboard} viewport={viewport} onRefresh={() => loadWorkspace({ soft: true })} onLogout={() => handleLogout()} />

        <div className="crm-toolbar">
          <div className="crm-toolbar-inputs">
            {activeView === "leads" || (activeView === "dashboard" && roleGroup !== "customer") ? (
              <input
                type="search"
                placeholder="Search leads by name, number, city, or source"
                value={leadSearch}
                onChange={(event) => setLeadSearch(event.target.value)}
              />
            ) : null}
            {["dashboard", "properties"].includes(activeView) ? (
              <input
                type="search"
                placeholder="Search properties by title, locality, city, or type"
                value={propertySearch}
                onChange={(event) => setPropertySearch(event.target.value)}
              />
            ) : null}
          </div>
          <div className="crm-toolbar-status">
            <span className="crm-badge crm-badge-neutral">{navLabel}</span>
            <span className="crm-badge crm-badge-neutral">{refreshing ? "Refreshing..." : `${notifications.filter((item) => !item.read_at).length} unread`}</span>
          </div>
        </div>

        <StatStrip items={statItems} />

        {message ? <div className="crm-banner crm-banner-success">{message}</div> : null}
        {error ? <div className="crm-banner crm-banner-danger">{error}</div> : null}

        <div className="crm-content">{renderActiveView()}</div>
      </main>
    </div>
  );
}
