import { EstadoVazio } from "./estado-vazio";
import { DetalhesTecnicos } from "./detalhes-tecnicos";

/** Painel sem fonte de dados (instalação incompleta). Instrução técnica
 *  fica colapsada — estado de operador, não de uso comum. */
export function SemDados() {
  return (
    <div className="mx-auto max-w-xl pt-16">
      <EstadoVazio
        titulo="O painel ainda não está conectado aos dados"
        descricao="Finalize a instalação para ver a sua operação aqui."
      />
      <DetalhesTecnicos
        rotulo="Detalhes técnicos (instalação)"
        itens={[
          ["operação local", "definir SQLITE_PATH no ambiente do painel"], // harness-ok
          ["operação em nuvem", "definir DATABASE_URL no ambiente do painel"],
        ]}
      />
    </div>
  );
}
