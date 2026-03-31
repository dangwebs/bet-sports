import React from "react";
import { Alert, Button } from "@mui/material";

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<{}, State> {
  constructor(props: {}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Here you could log to an error tracking service
    // console.error('ErrorBoundary caught', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20 }}>
          <Alert severity="error">
            Ocurrió un error en la aplicación. Por favor recarga la página.
          </Alert>
          <Button
            sx={{ mt: 2 }}
            variant="contained"
            onClick={() => window.location.reload()}
          >
            Recargar
          </Button>
        </div>
      );
    }
    return this.props.children as React.ReactElement;
  }
}
