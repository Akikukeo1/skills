# Skills

個人用の Agent Skills 集です。

## インストール・アップデート

初回インストールも更新も、次のコマンドを実行して対象のスキルを選択してください。

```sh
npx skills add Akikukeo1/skills
```

利用可能なスキルを確認するには:

```sh
npx skills add Akikukeo1/skills --list
```

## スキル

| 名前 | 内容 |
| --- | --- |
| [review-defects](skills/review-defects/SKILL.md) | 変更の振る舞い追跡・反例探索・障害経路・不変条件から不具合を探します。通常はStandard、重要な変更にはDeep監査を適用します。 |
| [review-conventions](skills/review-conventions/SKILL.md) | リポジトリ固有の規約、実装パターン、UI、テストの書き方との不整合を読み取り専用でレビューします。 |
| [release-audit](skills/release-audit/SKILL.md) | Gitリポジトリの公開・提出前に、秘密情報・履歴・個人情報・ライセンスを読み取り専用で監査します。匿名提出にも対応します。 |
