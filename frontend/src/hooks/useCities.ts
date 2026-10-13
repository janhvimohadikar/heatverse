import { api } from "../services/endpoints";
import { useAsync } from "./useAsync";

export function useCities() {
  const r = useAsync(() => api.cities().then((x) => x.items), []);
  return { cities: r.data ?? [], loading: r.loading, error: r.error, reload: r.reload };
}
