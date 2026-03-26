import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Signup from "./pages/Signup";
import Portal from "./pages/Portal";
import LandingPage from "./pages/LandingPage";
import "./styles/theme.css";

const isAuthenticated = () => {
  return !! sessionStorage.getItem("token");
};

const ProtectedRoute = ({ children }) => {
  return isAuthenticated() ? children : <Navigate to="/" />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
     
        <Route path="/signup-request" element={<Signup />} />

        <Route path="/" element={<LandingPage />} />

        <Route path="/portal" element={<ProtectedRoute>
              <Portal />
            </ProtectedRoute>} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Default route */}
        <Route
          path="*"
          element={<Navigate to={isAuthenticated() ? "/dashboard" : "/login"} />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
