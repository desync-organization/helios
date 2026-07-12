/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as adapters from "../adapters.js";
import type * as agents from "../agents.js";
import type * as alerts from "../alerts.js";
import type * as backlog from "../backlog.js";
import type * as controls from "../controls.js";
import type * as evals from "../evals.js";
import type * as events from "../events.js";
import type * as http from "../http.js";
import type * as ingest from "../ingest.js";
import type * as memory from "../memory.js";
import type * as policies from "../policies.js";
import type * as providers from "../providers.js";
import type * as repositories from "../repositories.js";
import type * as runtime from "../runtime.js";
import type * as security from "../security.js";
import type * as tasks from "../tasks.js";
import type * as writeback from "../writeback.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  adapters: typeof adapters;
  agents: typeof agents;
  alerts: typeof alerts;
  backlog: typeof backlog;
  controls: typeof controls;
  evals: typeof evals;
  events: typeof events;
  http: typeof http;
  ingest: typeof ingest;
  memory: typeof memory;
  policies: typeof policies;
  providers: typeof providers;
  repositories: typeof repositories;
  runtime: typeof runtime;
  security: typeof security;
  tasks: typeof tasks;
  writeback: typeof writeback;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};
