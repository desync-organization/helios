/**
 * Control buttons for the Multiverse view.
 * Provides add, remove, and merge operations for git branches.
 */
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2, GitMerge, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useGitStore } from "@/lib/git-store";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface MultiverseControlsProps {
  /** Currently selected universe (branch) */
  selectedBranch: string | null;
  /** Callback when a branch operation completes */
  onOperationComplete?: () => void;
}

/**
 * MultiverseControls component renders the left-side control panel
 * for managing git branches in the multiverse view.
 */
export function MultiverseControls({
  selectedBranch,
  onOperationComplete,
}: MultiverseControlsProps) {
  const { branches, createBranch, deleteBranch, mergeBranch, loading, error } =
    useGitStore();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDeleteSelectionDialog, setShowDeleteSelectionDialog] = useState(false);
  const [showDeleteConfirmDialog, setShowDeleteConfirmDialog] = useState(false);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [newBranchName, setNewBranchName] = useState("");
  const [branchToDelete, setBranchToDelete] = useState<string | null>(null);
  const [mergeFromBranch, setMergeFromBranch] = useState<string | null>(null);
  const [mergeToBranch, setMergeToBranch] = useState<string | null>(null);

  // Filter out active branch from deletable branches
  const deletableBranches = branches.filter((b) => !b.isActive);
  const mergeableBranches = branches.filter((b) => !b.isActive);

  /**
   * Handle creating a new branch with custom name.
   */
  const handleCreate = async () => {
    if (!newBranchName.trim()) return;
    
    // Validate branch name (basic git branch name rules)
    const validNamePattern = /^[a-zA-Z0-9/_-]+$/;
    if (!validNamePattern.test(newBranchName)) {
      return; // Could show error toast here
    }

    await createBranch(newBranchName);
    setNewBranchName("");
    setShowCreateDialog(false);
    onOperationComplete?.();
  };

  /**
   * Handle deleting a branch - opens confirmation after selection.
   */
  const handleDeleteSelection = () => {
    if (!branchToDelete) return;
    setShowDeleteSelectionDialog(false);
    setShowDeleteConfirmDialog(true);
  };

  /**
   * Execute the branch deletion.
   */
  const handleDeleteConfirm = async () => {
    if (!branchToDelete) return;
    await deleteBranch(branchToDelete);
    setBranchToDelete(null);
    setShowDeleteConfirmDialog(false);
    onOperationComplete?.();
  };

  /**
   * Handle merging branches - merge FROM source INTO target.
   */
  const handleMerge = async () => {
    if (!mergeFromBranch || !mergeToBranch) return;
    await mergeBranch(mergeFromBranch, mergeToBranch);
    setMergeFromBranch(null);
    setMergeToBranch(null);
    setShowMergeDialog(false);
    onOperationComplete?.();
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        className="fixed left-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-3 p-3 rounded-2xl bg-card/40 backdrop-blur-md border border-primary/10"
      >
        {/* Add Button */}
        <Button
          size="icon"
          className={cn(
            "h-14 w-14 rounded-full shadow-lg",
            "bg-secondary",
            "hover:bg-accent",
            "border-2 border-primary/50",
            "transition-all duration-200",
            "hover:scale-110 active:scale-95",
          )}
          onClick={() => setShowCreateDialog(true)}
          disabled={loading}
          title="Create new universe (branch)"
        >
          {loading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : (
            <Plus className="h-6 w-6" />
          )}
        </Button>

        {/* Remove Button - Opens dialog */}
        <Button
          size="icon"
          className={cn(
            "h-14 w-14 rounded-full shadow-lg",
            "bg-secondary",
            "hover:bg-accent",
            "border-2 border-primary/50",
            "transition-all duration-200",
            "hover:scale-110 active:scale-95",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
          onClick={() => setShowDeleteSelectionDialog(true)}
          disabled={loading || deletableBranches.length === 0}
          title="Delete universe (branch)"
        >
          <Trash2 className="h-6 w-6" />
        </Button>

        {/* Merge Button - Opens dialog with from/to selection */}
        <Button
          size="icon"
          className={cn(
            "h-14 w-14 rounded-full shadow-lg",
            "bg-secondary",
            "hover:bg-accent",
            "border-2 border-primary/50",
            "transition-all duration-200",
            "hover:scale-110 active:scale-95",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
          onClick={() => setShowMergeDialog(true)}
          disabled={loading || branches.length < 2}
          title="Merge universes (branches)"
        >
          <GitMerge className="h-6 w-6" />
        </Button>

        {/* Error indicator */}
        {error && (
          <div className="absolute -right-2 top-0 h-3 w-3 rounded-full bg-destructive animate-pulse" />
        )}
      </motion.div>

      {/* Create Branch Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Universe</DialogTitle>
            <DialogDescription>
              Enter a name for your new branch. Use letters, numbers, hyphens,
              underscores, and forward slashes.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="branch-name">Branch Name</Label>
              <Input
                id="branch-name"
                placeholder="feature/my-awesome-branch"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newBranchName.trim()) {
                    handleCreate();
                  }
                }}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateDialog(false);
                setNewBranchName("");
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={loading || !newBranchName.trim()}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Branch"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Selection Dialog */}
      <Dialog open={showDeleteSelectionDialog} onOpenChange={setShowDeleteSelectionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Universe</DialogTitle>
            <DialogDescription>
              Select a branch to delete. You cannot delete the currently active branch.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="branch-to-delete">Branch to Delete</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-mono text-sm"
                    id="branch-to-delete"
                  >
                    {branchToDelete || "Select branch..."}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[400px]">
                  <DropdownMenuLabel>Delete Branch</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {deletableBranches.length === 0 ? (
                    <DropdownMenuItem disabled>
                      No branches available to delete
                    </DropdownMenuItem>
                  ) : (
                    deletableBranches.map((branch) => (
                      <DropdownMenuItem
                        key={branch.id}
                        onClick={() => setBranchToDelete(branch.name)}
                        className="font-mono text-sm"
                      >
                        {branch.name}
                      </DropdownMenuItem>
                    ))
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {branchToDelete && (
              <div className="rounded-lg bg-muted p-3 text-sm">
                <p className="text-muted-foreground">
                  Branch{" "}
                  <span className="font-mono text-foreground">{branchToDelete}</span>
                  {" "}will be permanently deleted.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteSelectionDialog(false);
                setBranchToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteSelection}
              disabled={!branchToDelete}
            >
              Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteConfirmDialog} onOpenChange={setShowDeleteConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Universe</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the branch{" "}
              <span className="font-mono text-foreground">{branchToDelete}</span>
              ? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteConfirmDialog(false);
                setBranchToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete Branch"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Merge Dialog with From/To Selection */}
      <Dialog open={showMergeDialog} onOpenChange={setShowMergeDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Merge Universes</DialogTitle>
            <DialogDescription>
              Select which branch to merge from and into which branch.
              The target branch will receive the changes.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            {/* Merge FROM (source) */}
            <div className="grid gap-2">
              <Label htmlFor="merge-from">Merge From (Source)</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-mono text-sm"
                    id="merge-from"
                  >
                    {mergeFromBranch || "Select branch..."}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[400px]">
                  <DropdownMenuLabel>Source Branch</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {branches.map((branch) => (
                    <DropdownMenuItem
                      key={branch.id}
                      onClick={() => setMergeFromBranch(branch.name)}
                      className="font-mono text-sm"
                    >
                      {branch.name}
                      {branch.isActive && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          (current)
                        </span>
                      )}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Merge TO (target) */}
            <div className="grid gap-2">
              <Label htmlFor="merge-to">Merge Into (Target)</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-mono text-sm"
                    id="merge-to"
                  >
                    {mergeToBranch || "Select branch..."}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[400px]">
                  <DropdownMenuLabel>Target Branch</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {branches.map((branch) => (
                    <DropdownMenuItem
                      key={branch.id}
                      onClick={() => setMergeToBranch(branch.name)}
                      className="font-mono text-sm"
                      disabled={branch.name === mergeFromBranch}
                    >
                      {branch.name}
                      {branch.isActive && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          (current)
                        </span>
                      )}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {mergeFromBranch && mergeToBranch && (
              <div className="rounded-lg bg-muted p-3 text-sm">
                <p className="text-muted-foreground">
                  This will merge changes from{" "}
                  <span className="font-mono text-foreground">{mergeFromBranch}</span>
                  {" "}into{" "}
                  <span className="font-mono text-foreground">{mergeToBranch}</span>
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowMergeDialog(false);
                setMergeFromBranch(null);
                setMergeToBranch(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleMerge}
              disabled={loading || !mergeFromBranch || !mergeToBranch || mergeFromBranch === mergeToBranch}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Merging...
                </>
              ) : (
                "Merge Branches"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
