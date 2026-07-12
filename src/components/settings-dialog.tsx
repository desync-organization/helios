"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye,
  EyeOff,
  Github,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Unplug,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/lib/auth-store";

/* ------------------------------------------------------------------ */
/*  Vercel logo (inline SVG — Vercel's ▲ triangle)                     */
/* ------------------------------------------------------------------ */
function VercelLogo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 76 65"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const {
    isVercelConnected,
    vercelUser,
    isGithubConnected,
    githubInstallUrl,
    clearVercelAuth,
    setVercelAuth,
    hydrateFromServer,
  } = useAuthStore();

  const [vercelInput, setVercelInput] = useState("");
  const [showVercelToken, setShowVercelToken] = useState(false);
  const [vercelLoading, setVercelLoading] = useState(false);
  const [vercelError, setVercelError] = useState<string | null>(null);
  const [vercelSuccess, setVercelSuccess] = useState<string | null>(null);

  const [disconnecting, setDisconnecting] = useState<"vercel" | null>(null);

  // Hydrate auth state when the dialog opens
  useEffect(() => {
    if (open) {
      hydrateFromServer();
    }
  }, [open, hydrateFromServer]);

  /* ---- Vercel PAT ---- */

  const handleSaveVercelToken = async () => {
    if (!vercelInput.trim()) return;

    setVercelLoading(true);
    setVercelError(null);
    setVercelSuccess(null);

    try {
      const res = await fetch("/api/auth/vercel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: vercelInput.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        setVercelError(data.error || "Failed to save token.");
        return;
      }

      setVercelAuth(data.user, vercelInput.trim());
      setVercelSuccess(`Connected as ${data.user.name ?? data.user.username}`);
      setVercelInput("");
    } catch {
      setVercelError("Network error — is the dev server running?");
    } finally {
      setVercelLoading(false);
    }
  };

  const handleDisconnectVercel = async () => {
    setDisconnecting("vercel");
    try {
      await fetch("/api/auth/vercel", { method: "DELETE" });
      clearVercelAuth();
      setVercelSuccess(null);
    } catch {
      /* ignore */
    } finally {
      setDisconnecting(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md border-border/50 bg-card/95 backdrop-blur-xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            Integrations
          </DialogTitle>
          <DialogDescription>
            Connect your accounts to enable deployment and repository
            management.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* ─── Vercel ─────────────────────────────────────────── */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <VercelLogo className="h-4 w-4" />
              <h3 className="text-sm font-medium">Vercel</h3>
              {isVercelConnected && (
                <span className="ml-auto flex items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Connected
                </span>
              )}
            </div>

            {isVercelConnected && vercelUser ? (
              <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 px-3 py-2.5">
                <div className="flex flex-col">
                  <span className="text-sm font-medium">
                    {vercelUser.name ?? vercelUser.username}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {vercelUser.email}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDisconnectVercel}
                  disabled={disconnecting === "vercel"}
                  className="text-muted-foreground hover:text-destructive"
                >
                  {disconnecting === "vercel" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Unplug className="h-4 w-4" />
                  )}
                </Button>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="vercel-token" className="text-xs">
                    Personal Access Token
                  </Label>
                  <div className="relative">
                    <Input
                      id="vercel-token"
                      type={showVercelToken ? "text" : "password"}
                      placeholder="Paste your Vercel token…"
                      value={vercelInput}
                      onChange={(e) => {
                        setVercelInput(e.target.value);
                        setVercelError(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveVercelToken();
                      }}
                      className="pr-10 font-mono text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowVercelToken(!showVercelToken)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showVercelToken ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Error / success messages */}
                <AnimatePresence mode="wait">
                  {vercelError && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="flex items-center gap-1.5 text-xs text-destructive"
                    >
                      <XCircle className="h-3.5 w-3.5 shrink-0" />
                      {vercelError}
                    </motion.div>
                  )}
                </AnimatePresence>

                <Button
                  onClick={handleSaveVercelToken}
                  disabled={vercelLoading || !vercelInput.trim()}
                  className="w-full gap-2"
                  variant="secondary"
                >
                  {vercelLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <VercelLogo className="h-3.5 w-3.5" />
                  )}
                  Save Token
                </Button>
              </>
            )}

            <p className="text-xs text-muted-foreground">
              Used to deploy projects to your Vercel account.{" "}
              <a
                href="https://vercel.com/account/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 text-primary hover:underline"
              >
                Create one
                <ExternalLink className="h-3 w-3" />
              </a>
            </p>
          </section>

          {/* Divider */}
          <div className="h-px bg-border/50" />

          {/* ─── GitHub PAT ─────────────────────────────────────── */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Github className="h-4 w-4" />
              <h3 className="text-sm font-medium">GitHub</h3>
              {isGithubConnected && (
                <span className="ml-auto flex items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Connected
                </span>
              )}
            </div>

            {isGithubConnected ? (
              <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 px-3 py-2.5">
                <div className="flex flex-col">
                  <span className="text-sm font-medium">Hermes GitHub App</span>
                  <span className="text-xs text-muted-foreground">
                    Repository installation is active
                  </span>
                </div>
                {githubInstallUrl && (
                  <Button variant="ghost" size="sm" asChild>
                    <a href={githubInstallUrl} target="_blank" rel="noopener noreferrer" aria-label="Manage GitHub App installation">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </Button>
                )}
              </div>
            ) : (
              <Button className="w-full gap-2" variant="secondary" asChild={Boolean(githubInstallUrl)} disabled={!githubInstallUrl}>
                {githubInstallUrl ? (
                  <a href={githubInstallUrl} target="_blank" rel="noopener noreferrer">
                    <Github className="h-4 w-4" />
                    Install GitHub App
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ) : (
                  <span><Github className="mr-2 inline h-4 w-4" />GitHub App URL not configured</span>
                )}
              </Button>
            )}

            <p className="text-xs text-muted-foreground">
              Install on selected repositories. Credentials remain in the server-side
              write-back service and are never sent to this browser.
            </p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
