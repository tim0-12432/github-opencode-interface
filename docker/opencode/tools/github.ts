import "bun";
import { tool } from "@opencode-ai/plugin";
import { Octokit } from "octokit";

function getOctokitClient(token: string) {
    return new Octokit({ auth: token });
}

export const getLabels = tool({
  description: "Get all available labels in the repository.",
  args: {},
  async execute() {
    const authToken = Bun.env.GITHUB_TOKEN;
    const repoName = Bun.env.REPO;
    const client = getOctokitClient(authToken!);
    const labelResult = await client.rest.issues.listLabelsForRepo({
        owner: repoName!.split("/")[0],
        repo: repoName!.split("/")[1],
    });
    return labelResult.data.map(label => label.name).join(", ");
  }
});

export const getAllCommentsOnIssue = tool({
  description: "Get all comments on a GitHub issue.",
  args: {
    issueNr: tool.schema.number().describe("Issue Number"),
  },
  async execute(args) {
    const authToken = Bun.env.GITHUB_TOKEN;
    const repoName = Bun.env.REPO;
    const client = getOctokitClient(authToken!);
    const commentsResult = await client.rest.issues.listComments({
        owner: repoName!.split("/")[0],
        repo: repoName!.split("/")[1],
        issue_number: args.issueNr,
    });
    return commentsResult.data.map(comment => comment.body || "").join("\n---\n");
  },
});

export const getAllSimilarIssues = tool({
  description: "Get all similar issues on a GitHub repository based on a title.",
  args: {
    issueTitle: tool.schema.string().describe("Issue Title"),
  },
  async execute(args) {
    const authToken = Bun.env.GITHUB_TOKEN;
    const repoName = Bun.env.REPO;
    const client = getOctokitClient(authToken!);
    const searchResult = await client.rest.search.issuesAndPullRequests({
        q: `${args.issueTitle} repo:${repoName} type:issue`,
    });
    return searchResult.data.items.map(issue => ({
        number: issue.number,
        title: issue.title,
        body: issue.body || "",
    })).join("\n---\n");
  }
});
