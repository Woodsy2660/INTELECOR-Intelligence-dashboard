import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview"   element={<Overview />} />
          <Route path="financial"  element={<Placeholder title="Financial" />} />
          <Route path="operations" element={<Placeholder title="Operations" />} />
          <Route path="documents"  element={<Placeholder title="Documents" />} />
          <Route path="settings"   element={<Placeholder title="Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
