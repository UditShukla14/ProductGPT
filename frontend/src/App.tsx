import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { AppHeader } from "@/components/AppHeader"
import { HvacPage } from "@/pages/HvacPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { ShopifyPage } from "@/pages/ShopifyPage"

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-svh w-full max-w-[100vw] overflow-x-clip bg-background">
        <AppHeader />
        <Routes>
          <Route path="/" element={<HvacPage />} />
          <Route path="/shopify" element={<ShopifyPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
