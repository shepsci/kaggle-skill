---
expect:
  request.writeUpId: number
---
{
  "id": 5001,
  "topic_id": 9001,
  "slug": "team-alpha-writeup",
  "title": "3rd place: boosted trees all the way down",
  "subtitle": "Target encoding and careful validation",
  "authors": "Team Alpha",
  "message": {
    "raw_markdown": "# Our approach\n\nWe used a gradient-boosting ensemble (LightGBM, XGBoost, CatBoost) with target encoding of the categorical columns and five-fold validation grouped by customer.\n\n## What did not work\n\nNeural networks and stacking more than two levels."
  },
  "write_up_links": []
}
