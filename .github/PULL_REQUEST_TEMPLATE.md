## 📌 Descrição das Alterações
<!-- Descreva de forma clara e objetiva o que foi implementado, corrigido ou refatorado. -->

## 🎯 Tipo de Mudança
- [ ] Nova funcionalidade / animação
- [ ] Correção de bug (*bugfix*)
- [ ] Refatoração ou otimização de código
- [ ] Atualização de documentação
- [ ] Ajuste em testes ou CI/CD

## 🧪 Checklist de Verificação
Antes de submeter este Pull Request para aprovação, certifique-se de que:
- [ ] O código segue a restrição de **não usar OpenGL, NumPy ou bibliotecas 3D externas**.
- [ ] A suíte de testes passou localmente sem erros:
  ```bash
  python -m unittest discover -s "Atividade AP1" -p "test_*.py"
  ```
- [ ] O teste de fumaça de ponta a ponta passou:
  ```bash
  python "Atividade AP1/test_ap1.py" --smoke
  ```
- [ ] Não foram incluídos arquivos temporários, logs ou lixo de compilação (`__pycache__`, etc.).

---
*Lembre-se: Este repositório exige a revisão e aprovação formal do proprietário (@gblsun) antes do merge na branch `main`.*
