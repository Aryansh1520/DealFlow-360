import { apiClient } from "@/lib/api-client";
import type { MetaEnums } from "@/lib/api/types";

export const metaApi = {
  enums: async (): Promise<MetaEnums> => {
    const { data } = await apiClient.get<MetaEnums>("/meta/enums");
    return data;
  },
};
