import { useEffect, useState } from "react";

export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let mounted = true;
    setState({ loading: true, error: null, data: null });
    fn()
      .then((data) => mounted && setState({ loading: false, error: null, data }))
      .catch((error) => mounted && setState({ loading: false, error, data: null }));
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
