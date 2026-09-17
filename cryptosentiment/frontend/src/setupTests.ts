// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach } from "@jest/globals";

// Explicit cleanup — some RTL v16 + React 19 combos don't auto-clean.
afterEach(() => {
  cleanup();
});
