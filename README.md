# ADempiere – Reverse engineering de la base de données

Outils et analyses pour le reverse engineering de la base de données d'[ADempiere](https://github.com/adempiere/adempiere).

Le code analysé n'est **pas** copié dans ce dépôt : il est référencé comme submodule Git dans `target/`, figé sur un commit précis.

## Initialisation

```bash
git clone --recurse-submodules --shallow-submodules <url-de-ce-repo>
```

Si le dépôt a déjà été cloné sans les submodules :

```bash
git submodule update --init --depth 1
```

Vérification :

```bash
git submodule status
# 4ae098fd18065f1a658ff56de3b90e63aabfecb2 target
```

## Version analysée

| | |
|---|---|
| Dépôt | `adempiere/adempiere` |
| Commit | [`4ae098f`](https://github.com/adempiere/adempiere/commit/4ae098fd18065f1a658ff56de3b90e63aabfecb2) |
| Licence | GPL v2 |

Toutes les analyses de ce dépôt portent sur cette version.

### Comment ce commit a été figé

```bash
SHA=4ae098fd18065f1a658ff56de3b90e63aabfecb2
git submodule add --depth 1 https://github.com/adempiere/adempiere.git target
git -C target fetch --depth 1 origin "$SHA"
git -C target checkout "$SHA"
git config -f .gitmodules submodule.target.shallow true
git add .gitmodules target
git commit -m "Pin ADempiere at ${SHA:0:7}"
```

Le clone est *shallow* (profondeur 1) : seul ce commit est téléchargé, pas l'historique complet d'ADempiere.

### Changer de version

```bash
git -C target fetch --depth 1 origin <nouveau-sha>
git -C target checkout <nouveau-sha>
git add target
git commit -m "Bump ADempiere to <nouveau-sha>"
```

Mettre ensuite à jour le tableau ci-dessus.

## Règles

- Ne jamais modifier le code dans `target/` : il sert uniquement de référence.
- Ne pas commiter de dumps contenant des données réelles.
