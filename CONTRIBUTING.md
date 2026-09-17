# Diretrizes de Contribuição e Políticas de Branch

Este repositório adota políticas rígidas de proteção de branch para assegurar a estabilidade do código, a conformidade com as restrições didáticas da disciplina e a integridade da suíte de testes.

---

## 🚫 Regra Geral: Commits Diretos na `main` São Proibidos

A branch `main` é protegida. Ninguém (com exceção do administrador para casos de emergência) pode commitar ou dar push diretamente nela. **Toda e qualquer contribuição deve obrigatoriamente passar por um Pull Request (PR) e receber o aval de aprovação de `@gblsun`.**

---

## 🔄 Fluxo de Trabalho Passo a Passo

### 1. Atualize a sua branch local `main`
Antes de iniciar qualquer trabalho, garanta que você está com a versão mais recente:
```bash
git checkout main
git pull origin main
```

### 2. Crie uma branch temática para sua alteração
Nunca trabalhe diretamente na `main`. Crie uma branch com nome descritivo:
```bash
# Para novas funcionalidades / elementos:
git checkout -b feature/nome-da-funcionalidade

# Para correções de bugs:
git checkout -b fix/descricao-do-problema

# Para documentação:
git checkout -b docs/nome-da-melhoria
```

### 3. Desenvolva e teste localmente
Lembre-se das regras fundamentais da disciplina:
- **Proibido usar OpenGL, motores 3D ou NumPy.** Todo cálculo deve ser analítico em Python puro com Pygame.
- Certifique-se de que os testes estão passando:
```bash
# Roda a suíte de testes unitários:
python -m unittest discover -s "Atividade AP1" -p "test_*.py"

# Roda o checklist automatizado (smoke test):
python "Atividade AP1/test_ap1.py" --smoke
```

### 4. Faça o commit e envie sua branch para o GitHub
```bash
git add .
git commit -m "tipo: descrição clara do que foi feito"
git push origin feature/nome-da-funcionalidade
```

### 5. Abra um Pull Request (PR)
1. Acesse a página do repositório no GitHub: [gblsun/space-station-pygame](https://github.com/gblsun/space-station-pygame).
2. O GitHub sugerirá a abertura do PR para a sua branch recém-enviada.
3. Preencha os campos do modelo de Pull Request (descrição e checklist).
4. O GitHub atribuirá automaticamente `@gblsun` como revisor obrigatório através das regras do [`CODEOWNERS`](.github/CODEOWNERS).

### 6. Aguarde a Revisão e Aprovação
- O pipeline de CI/CD do GitHub Actions executará os testes automaticamente no seu PR.
- **O merge só será liberado após a aprovação formal de `@gblsun`** e com todos os testes automatizados verdes.
- Se forem solicitadas alterações, faça novos commits na mesma branch e envie via `git push`. A aprovação anterior será descartada automaticamente caso novos commits sejam adicionados após o review.
