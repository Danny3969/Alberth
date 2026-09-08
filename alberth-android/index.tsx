import { registerRootComponent } from 'expo';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, StatusBar } from 'react-native';
import App from './App';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// Global exception shield for unhandled promises and background errors
declare const ErrorUtils: any;
if (typeof ErrorUtils !== 'undefined' && ErrorUtils.setGlobalHandler) {
  const defaultHandler = ErrorUtils.getGlobalHandler && ErrorUtils.getGlobalHandler();
  ErrorUtils.setGlobalHandler((error: any, isFatal?: boolean) => {
    console.warn('[Alberth Global Exception Shield Intercepted]:', error?.message || error);
    if (defaultHandler && !isFatal) {
      defaultHandler(error, false);
    }
  });
}

// ─── Sci-Fi Quantum Emergency Recovery Boundary ─────────────────────────────
class GlobalErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[Alberth Crash Intercepted]', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  handleRestart = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <View style={recoveryStyles.container}>
          <StatusBar barStyle="light-content" backgroundColor="#040711" />
          <View style={recoveryStyles.card}>
            <View style={recoveryStyles.headerRow}>
              <View style={recoveryStyles.glowBadge}>
                <Text style={recoveryStyles.badgeText}>SISTEMA DE RECUPERACIÓN</Text>
              </View>
            </View>

            <Text style={recoveryStyles.title}>ALBERTH QUANTUM CORE</Text>
            <Text style={recoveryStyles.subtitle}>
              El núcleo interceptó un error de ejecución nativo antes de detener la app.
            </Text>

            <View style={recoveryStyles.errorBox}>
              <ScrollView style={{ maxHeight: 220 }}>
                <Text style={recoveryStyles.errorLabel}>Detalle del diagnóstico:</Text>
                <Text style={recoveryStyles.errorMsg}>
                  {this.state.error?.name}: {this.state.error?.message || 'Error desconocido'}
                </Text>
                {this.state.errorInfo?.componentStack ? (
                  <Text style={recoveryStyles.stackTrace}>
                    {this.state.errorInfo.componentStack.trim().slice(0, 400)}
                  </Text>
                ) : null}
              </ScrollView>
            </View>

            <TouchableOpacity style={recoveryStyles.btn} onPress={this.handleRestart}>
              <Text style={recoveryStyles.btnText}>REINICIAR NÚCLEO ALBERTH</Text>
            </TouchableOpacity>
          </View>
        </View>
      );
    }

    return this.props.children;
  }
}

const recoveryStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#040711',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  card: {
    width: '100%',
    backgroundColor: '#060c1a',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    padding: 24,
    shadowColor: '#00f0ff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 8,
  },
  headerRow: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  glowBadge: {
    backgroundColor: 'rgba(255, 42, 95, 0.15)',
    borderColor: 'rgba(255, 42, 95, 0.5)',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: {
    color: '#ff2a5f',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  title: {
    color: '#00f0ff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  subtitle: {
    color: '#8b9bb4',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 16,
  },
  errorBox: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    marginBottom: 20,
  },
  errorLabel: {
    color: '#f0c060',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  errorMsg: {
    color: '#f0f6fc',
    fontSize: 12,
    fontFamily: 'monospace',
    marginBottom: 8,
  },
  stackTrace: {
    color: '#51627b',
    fontSize: 10,
    fontFamily: 'monospace',
  },
  btn: {
    backgroundColor: '#00f0ff',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnText: {
    color: '#040711',
    fontWeight: '900',
    fontSize: 13,
    letterSpacing: 1,
  },
});

function Root() {
  return (
    <GlobalErrorBoundary>
      <SafeAreaProvider>
        <App />
      </SafeAreaProvider>
    </GlobalErrorBoundary>
  );
}

registerRootComponent(Root);
