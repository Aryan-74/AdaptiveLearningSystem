import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.resource_service import load_resource_catalog, retrieve_real_resources_for_area, validate_canonical_resource

def run_tests():
    catalog = load_resource_catalog()
    total_resources = len(catalog)
    video_resources = [r for r in catalog if map_to_video(r.get("type"))]
    print(f"Total resources loaded from data/resource_catalog.json: {total_resources}")
    print(f"Total Video resources loaded from data/resource_catalog.json: {len(video_resources)}")

    # Test cases: A. Variables, B. Conditions, C. Loops, D. Functions
    tests = [
        ("A. Variables weakness", "variables", "RES-PY-VAR-03", "https://www.youtube.com/watch?v=rfscVS0vtbw"),
        ("B. Conditions weakness", "conditions", "RES-PY-COND-03", "https://www.youtube.com/watch?v=DZwmZ8Usvnk"),
        ("C. Loops weakness", "loops", "RES-PY-LOOP-03", "https://www.youtube.com/watch?v=6iF8Xb7Z3wQ"),
        ("D. Functions weakness", "functions", "RES-PY-FUNC-03", "https://www.youtube.com/watch?v=9OSy885P8_g")
    ]

    all_passed = True
    for test_name, topic, expected_id, expected_url in tests:
        res_list = retrieve_real_resources_for_area(topic, "python")
        yt_resources = [r for r in res_list if r.get("type") == "Video" and "youtube.com" in r.get("url", "")]
        
        print(f"\n--- {test_name} ({topic}) ---")
        print(f"Total retrieved for area: {len(res_list)}")
        print(f"YouTube videos retrieved: {len(yt_resources)}")
        
        found = False
        for r in yt_resources:
            print(f"  - Title: {r['title']}")
            print(f"    Type: {r['type']}")
            print(f"    Source: {r['source']}")
            print(f"    URL: {r['url']}")
            print(f"    Reason: {r['reason']}")

            if r.get("url") == expected_url:
                found = True
                # Validate URL structure & rules
                assert r["type"] == "Video"
                assert r["url"].startswith("https://")
                assert "youtube.com" in r["url"]
                assert r["title"]
                assert r["source"]
        
        if found:
            print(f"STATUS: PASSED (Found real YouTube video matching expected URL)")
        else:
            print(f"STATUS: FAILED (Did not find expected YouTube URL: {expected_url})")
            all_passed = False

    print("\n==========================================")
    if all_passed:
        print("ALL 4 YOUTUBE TESTS PASSED OK!")
    else:
        print("SOME YOUTUBE TESTS FAILED.")
        sys.exit(1)

def map_to_video(raw_type):
    return raw_type and "video" in str(raw_type).lower()

if __name__ == "__main__":
    run_tests()
