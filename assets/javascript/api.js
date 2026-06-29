import {Configuration} from "api-client";
import {getCsrfToken} from "./csrf";


export function getApiConfiguration(serverBaseUrl) {
  return new Configuration({
    basePath: serverBaseUrl,
    headers: getApiHeaders(),
  });
}

export function getApiHeaders() {
  return {
    'X-CSRFToken': getCsrfToken(),
  }
}
