import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    user: {
      id: number;
      email: string;
      name: string;
      image?: string;
      isAdmin: boolean;
    };
  }

  interface User {
    id: number;
    isAdmin: boolean;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId: number;
    isAdmin: boolean;
  }
}
