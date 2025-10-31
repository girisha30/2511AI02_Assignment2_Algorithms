import streamlit as st
import pandas as pd
import os
from logger_config import get_logger
from allocator import (
    allocate_sorted_by_cgpa,
    map_allocations_to_original,
    build_fac_preference_count,
)

logger = get_logger(__name__)

st.set_page_config(page_title="Automatic Faculty–Student Allocation System", layout="wide")
st.title("Automatic Faculty–Student Allocation System")


uploaded = st.file_uploader("Upload input CSV", type=["csv"])


def df_to_bytes(df: pd.DataFrame) -> bytes:
    """Convert dataframe to CSV bytes (no index)."""
    return df.to_csv(index=False).encode("utf-8")


def save_outputs(final_alloc_df: pd.DataFrame, fac_pref_df: pd.DataFrame):
    """Save outputs to outputs/ directory (useful for Docker / grader)."""
    try:
        os.makedirs("outputs", exist_ok=True)
        final_alloc_df.to_csv(os.path.join("outputs", "output_btp_mtp_allocation.csv"), index=False)
        fac_pref_df.to_csv(os.path.join("outputs", "fac_preference_count.csv"), index=False)
        logger.info("Saved outputs to outputs/ directory")
    except Exception:
        logger.exception("Failed to save outputs to disk")
        raise


try:
    if uploaded is not None:
        # Read uploaded CSV
        try:
            original_df = pd.read_csv(uploaded, index_col=False)
        except Exception as e:
            logger.exception("Failed to read uploaded CSV")
            st.error(f"Failed to read uploaded CSV: {e}")
            raise

        st.subheader("Input preview (first 10 rows)")
        st.dataframe(original_df.head(10))

        try:
            # 1) compute allocation on CGPA-sorted dataframe (internal mapping to names happens in allocator)
            alloc_sorted = allocate_sorted_by_cgpa(original_df.copy())

            # 2) map allocations back to original order; final_alloc contains only columns up to CGPA + AllocatedFaculty
            final_alloc = map_allocations_to_original(original_df.copy(), alloc_sorted)

            # 3) build faculty preference counts per rank (Fac, Count Pref 1..N)
            fac_pref_df = build_fac_preference_count(original_df.copy())

            # Defensive: ensure 'Fac' is a column and not DataFrame index
            if "Fac" not in fac_pref_df.columns:
                fac_pref_df = fac_pref_df.reset_index().rename(columns={"index": "Fac"})
            fac_pref_df = fac_pref_df.reset_index(drop=True)

            # Show previews (clean)
            st.subheader("Final allocation (first 20 rows)")
            st.dataframe(final_alloc.head(20))

            st.subheader("Faculty preference counts ")
            st.dataframe(fac_pref_df.head(40))

            # Provide download buttons (exact filenames)
            st.download_button(
                "Download output_btp_mtp_allocation.csv",
                data=df_to_bytes(final_alloc),
                file_name="output_btp_mtp_allocation.csv",
                mime="text/csv",
            )

            st.download_button(
                "Download fac_preference_count.csv",
                data=df_to_bytes(fac_pref_df),
                file_name="fac_preference_count.csv",
                mime="text/csv",
            )

            # Save to disk for Docker/grader
            save_outputs(final_alloc, fac_pref_df)

            st.success("Outputs generated. Use the download buttons or check the outputs/ folder.")
        except Exception as e:
            logger.exception("Allocation pipeline error")
            st.error(f"Allocation pipeline error: {e}")

    else:
        st.info("No file uploaded yet. Upload your input CSV (input_btp_mtp_allocation.csv).")
        # if st.button("Run example_input.csv (if present)"):
        #     try:
        #         example = pd.read_csv("example_input.csv", index_col=False)
        #         alloc_sorted = allocate_sorted_by_cgpa(example.copy())
        #         final_alloc = map_allocations_to_original(example.copy(), alloc_sorted)
        #         fac_pref_df = build_fac_preference_count(example.copy())

        #         # Ensure 'Fac' present
        #         if "Fac" not in fac_pref_df.columns:
        #             fac_pref_df = fac_pref_df.reset_index().rename(columns={"index": "Fac"})
        #         fac_pref_df = fac_pref_df.reset_index(drop=True)

        #         st.subheader("Example final allocation (first 20 rows)")
        #         st.dataframe(final_alloc.head(20))

        #         st.subheader("Example faculty preference counts (first 40 rows)")
        #         st.dataframe(fac_pref_df.head(40))

        #         st.download_button(
        #             "Download example allocation",
        #             data=df_to_bytes(final_alloc),
        #             file_name="output_btp_mtp_allocation_example.csv",
        #             mime="text/csv",
        #         )
        #         st.download_button(
        #             "Download example fac pref",
        #             data=df_to_bytes(fac_pref_df),
        #             file_name="fac_preference_count_example.csv",
        #             mime="text/csv",
        #         )

        #         save_outputs(final_alloc, fac_pref_df)
        #         st.success("Example outputs saved to outputs/ folder.")
        #     except FileNotFoundError:
        #         st.error("example_input.csv not found in project root.")
        #     except Exception as e:
        #         logger.exception("Example run failed")
        #         st.error(f"Example run failed: {e}")

except Exception as e:
    logger.exception("Unexpected app error")
    st.error("Unexpected error occurred. Check logs.")
