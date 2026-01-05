import React, { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Button,
  IconButton,
  Tooltip,
} from "@mui/material";
import { SportsSoccer, GetApp, SmartToy, Dashboard } from "@mui/icons-material";
import OfflineIndicator from "../../components/common/OfflineIndicator";
import { usePWAInstall } from "../../../hooks/usePWAInstall";
import { useBotStore } from "../../../application/stores/useBotStore";

interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { installPrompt, isInstalled, handleInstallClick } = usePWAInstall();
  const { trainingStatus } = useBotStore();
  const location = useLocation();
  const isPredictions = location.pathname === "/";

  // Only show the bot icon if training is fully completed
  const showBotIcon = trainingStatus === "COMPLETED";

  return (
    <>
      <Box
        sx={{
          minHeight: "100vh",
          // Background handled by theme/CssBaseline
          bgcolor: "background.default",
        }}
      >
        {/* Navigation */}
        <AppBar
          position="static"
          elevation={0}
          className="glass-header"
          sx={{
            background: "transparent", // Handled by CSS class
          }}
        >
          <Toolbar>
            <SportsSoccer sx={{ mr: 2, color: "primary.main" }} />
            <Typography
              variant="h6"
              component="h1"
              sx={{ flexGrow: 1, fontWeight: 700 }}
            >
              BJJ - BetSports
            </Typography>
            {showBotIcon && (
              <Tooltip
                title={
                  isPredictions ? "Ir al Bot de Inversión" : "Ver Predicciones"
                }
              >
                <Link
                  to={isPredictions ? "/bot" : "/"}
                  style={{ textDecoration: "none" }}
                >
                  <IconButton sx={{ color: "white", mr: 1 }}>
                    {isPredictions ? <SmartToy /> : <Dashboard />}
                  </IconButton>
                </Link>
              </Tooltip>
            )}

            {installPrompt && !isInstalled && (
              <Button
                variant="outlined"
                color="primary"
                size="small"
                startIcon={<GetApp />}
                onClick={handleInstallClick}
                sx={{ ml: 2 }}
              >
                Instalar App
              </Button>
            )}
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: 4 }} className="page-transition">
          {children}
        </Container>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: 8,
            pt: 4,
            pb: 4,
            borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Modelos predictivos basados en datos estadísticos de alto
            rendimiento.
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ display: "block", mb: 2, maxWidth: 800, mx: "auto" }}
          >
            Fuentes de datos: Football-Data.org, API-Football,
            Football-Data.co.uk, TheSportsDB, ESPN, ClubElo, Understat, FotMob,
            The Odds API, ScoreBat y OpenFootball. Las predicciones son
            probabilísticas y no garantizan resultados. Juegue con
            responsabilidad.
          </Typography>
          <Typography variant="caption" color="text.disabled" display="block">
            © 2025 BJJ - BetSports
          </Typography>
        </Box>
      </Box>

      {/* Offline Status Indicators */}
      <OfflineIndicator />
    </>
  );
};

export default MainLayout;
