"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Login() {
  const r = useRouter();
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function entrar(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setCarregando(true); setErro("");
    const dados = new FormData(e.currentTarget);
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: dados.get("email"), senha: dados.get("senha") }),
    });
    if (resp.ok) r.push("/");
    else setErro((await resp.json()).erro ?? "falha no login");
    setCarregando(false);
  }

  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <form onSubmit={entrar}
        className="w-full max-w-sm rounded-2xl border border-linha bg-carta p-8">
        <h1 className="text-lg font-semibold">
          afilify<span className="text-acento">.</span>
        </h1>
        <p className="mt-1 text-sm text-tinta2">Entre para operar</p>
        <label className="mt-6 block text-xs text-tinta2">E-mail
          <input name="email" type="email" required autoComplete="username"
            className="mt-1 w-full rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm text-tinta outline-none focus:border-acento" />
        </label>
        <label className="mt-4 block text-xs text-tinta2">Senha
          <input name="senha" type="password" required autoComplete="current-password"
            className="mt-1 w-full rounded-lg border border-linha bg-carta2 px-3 py-2 text-sm text-tinta outline-none focus:border-acento" />
        </label>
        {erro && <p className="mt-3 text-sm text-erro">{erro}</p>}
        <button disabled={carregando}
          className="mt-6 w-full rounded-lg bg-acento px-4 py-2 text-sm font-semibold text-fundo disabled:opacity-60">
          {carregando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
