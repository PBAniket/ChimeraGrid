import pandas as pd
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    send_file,
    Response,
)
import urllib.parse
import io
import os
import random

import transformer as transformer_service

app = Flask(__name__)

uploaded_dataframes = {}
df_counter = 0


def url_encode_filter(s):
    return urllib.parse.quote_plus(str(s))


app.jinja_env.filters["url_encode"] = url_encode_filter


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/transformer")
def transformer_entry():
    global df_counter
    uploaded_dataframes.clear()
    df_counter = 0
    return redirect(url_for("index"))


@app.route("/index")
def index():
    if not uploaded_dataframes:
        global df_counter
        uploaded_dataframes.clear()
        df_counter = 0
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_files():
    global df_counter

    files = request.files.getlist("file")
    if not files:
        if uploaded_dataframes:
            return redirect(url_for("define_transformations"))
        else:
            return Response("No files selected for upload.", status=400)

    processed_any_file_in_this_batch = False
    for file in files:
        if file.filename:
            filename = file.filename

            for existing_df_id, existing_df_info in list(uploaded_dataframes.items()):
                if (
                    isinstance(existing_df_info, dict)
                    and "filename" in existing_df_info
                    and existing_df_info["filename"] == filename
                ):
                    del uploaded_dataframes[existing_df_id]
                    break

            try:
                if filename.lower().endswith(".csv"):
                    df = pd.read_csv(file)
                elif filename.lower().endswith(".json"):
                    df = pd.read_json(file)
                else:
                    continue

                df_id = str(df_counter)
                df_counter += 1
                uploaded_dataframes[df_id] = {
                    "df": df.copy(),
                    "original_df": df.copy(),
                    "filename": filename,
                }
                processed_any_file_in_this_batch = True

            except Exception as e:
                pass

    if not processed_any_file_in_this_batch and not uploaded_dataframes:
        return Response(
            "No new files could be processed. Please try again with valid CSV/JSON files.",
            status=400,
        )

    return redirect(url_for("define_transformations"))


@app.route("/define_transformations")
def define_transformations():
    if not uploaded_dataframes:
        return redirect(url_for("index"))

    filtered_uploaded_dataframes = {
        df_id: data_info
        for df_id, data_info in uploaded_dataframes.items()
        if isinstance(data_info, dict) and "df" in data_info and "filename" in data_info
    }
    return render_template("column_selection.html", files=filtered_uploaded_dataframes)


@app.route("/display_samples", methods=["POST"])
def display_samples():
    samples_by_file = {}
    for df_id, df_info in uploaded_dataframes.items():
        if not (
            isinstance(df_info, dict) and "df" in df_info and "filename" in df_info
        ):
            continue

        selected_columns = request.form.getlist(f"selected_columns_{df_id}")

        if not selected_columns:
            samples_by_file[df_id] = {}
            continue

        df = df_info["df"]
        samples = {}
        for col in selected_columns:
            unique_non_na_values = df[col].dropna().astype(str).unique()
            samples[col] = random.sample(
                list(unique_non_na_values), min(len(unique_non_na_values), 5)
            )

        samples_by_file[df_id] = samples

    return render_template(
        "sample_display.html",
        samples_by_file=samples_by_file,
        files=uploaded_dataframes,
    )


@app.route("/provide_targets", methods=["POST"])
def provide_targets():
    columns_by_file = {}
    for df_id in uploaded_dataframes:
        df_info = uploaded_dataframes.get(df_id)
        if not (
            isinstance(df_info, dict) and "df" in df_info and "filename" in df_info
        ):
            continue

        cols_for_this_file = {}
        for key in request.form:
            if key.startswith(f"samples_{df_id}_"):
                col_name_encoded = key.replace(f"samples_{df_id}_", "", 1)
                col_name = urllib.parse.unquote_plus(col_name_encoded)
                sample_values = urllib.parse.unquote_plus(request.form.get(key)).split(
                    "|||"
                )
                cols_for_this_file[col_name] = sample_values
        columns_by_file[df_id] = cols_for_this_file

    return render_template(
        "target_input.html", columns_by_file=columns_by_file, files=uploaded_dataframes
    )


@app.route("/review_transformations", methods=["POST"])
def review_transformations():
    tasks_by_col = {}

    for key, value in request.form.items():
        if key.startswith("input_mode_"):
            parts = key.split("_", 3)
            df_id, col_name_encoded = parts[2], parts[3]
            col_name = urllib.parse.unquote_plus(col_name_encoded)

            if df_id not in tasks_by_col:
                tasks_by_col[df_id] = {}

            if value == "prompt":
                prompt_text = request.form.get(
                    f"prompt_text_{df_id}_{col_name_encoded}"
                )
                samples_str = request.form.get(
                    f"source_samples_{df_id}_{col_name_encoded}", ""
                )
                samples = urllib.parse.unquote_plus(samples_str).split("|||")
                tasks_by_col[df_id][col_name] = {
                    "mode": "prompt",
                    "prompt": prompt_text,
                    "samples": samples,
                }
            else:
                tasks_by_col[df_id][col_name] = {"mode": "examples", "examples": []}

    for key, value in request.form.items():
        if key.startswith("source_val_"):
            parts = key.split("_", 4)
            df_id, col_name_encoded, index = parts[2], parts[3], parts[4]
            col_name = urllib.parse.unquote_plus(col_name_encoded)

            if df_id in tasks_by_col and col_name in tasks_by_col[df_id]:
                if tasks_by_col[df_id][col_name]["mode"] == "examples":
                    source_val = urllib.parse.unquote_plus(value)
                    target_val = request.form.get(
                        f"target_val_{df_id}_{col_name_encoded}_{index}"
                    )
                    tasks_by_col[df_id][col_name]["examples"].append(
                        (source_val, target_val)
                    )

    review_data_by_file = {}
    for df_id, columns in tasks_by_col.items():
        review_data_by_file[df_id] = []
        for col_name, task in columns.items():
            if task["mode"] == "prompt":
                prompt = task["prompt"]
                samples = task["samples"]
                code = transformer_service.get_llm_transformation_function_from_prompt(
                    prompt, samples
                )
                review_data_by_file[df_id].append(
                    {
                        "col_name": col_name,
                        "type": "Prompt",
                        "input_method": "prompt",
                        "prompt": prompt,
                        "samples": samples,
                        "code": code,
                    }
                )
            else:
                examples = task["examples"]
                code = transformer_service.get_llm_transformation_function(examples)
                review_data_by_file[df_id].append(
                    {
                        "col_name": col_name,
                        "type": "Examples",
                        "input_method": "examples",
                        "examples": examples,
                        "code": code,
                    }
                )

    uploaded_dataframes["master_review_data"] = review_data_by_file

    filtered_files_for_template = {
        df_id: data_info
        for df_id, data_info in uploaded_dataframes.items()
        if isinstance(data_info, dict) and "df" in data_info and "filename" in data_info
    }

    return render_template(
        "review_transformation.html",
        review_data_by_file=review_data_by_file,
        files=filtered_files_for_template,
    )


@app.route("/process_transformation", methods=["POST"])
def process_transformation():
    rules_by_file = uploaded_dataframes.get("master_review_data", {})
    if not rules_by_file:
        return (
            "Error: No transformation rules found in session. Please start over.",
            400,
        )

    batch_results = {}
    for df_id, rules_to_apply in rules_by_file.items():
        if df_id not in uploaded_dataframes:
            continue

        df_info = uploaded_dataframes[df_id]
        if not (
            isinstance(df_info, dict) and "df" in df_info and "original_df" in df_info
        ):
            continue

        current_df = df_info["df"].copy()
        successful_reports, errors = {}, {}

        for rule in rules_to_apply:
            col_name, function_code = rule["col_name"], rule["code"]
            try:
                if (
                    not function_code
                    or "LLM failed" in function_code
                    or "API Error" in function_code
                ):
                    errors[col_name] = "Invalid or missing transformation code."
                    continue

                transform_func = (
                    transformer_service.create_and_execute_transform_function(
                        function_code
                    )
                )
                if not transform_func:
                    errors[col_name] = "Code execution failed."
                    continue

                new_column_data = transformer_service.apply_transformation_to_column(
                    current_df, col_name, transform_func
                )
                health_report = transformer_service.generate_health_report(
                    df_info["original_df"][col_name], new_column_data
                )
                successful_reports[col_name] = health_report
                current_df[col_name] = new_column_data

            except Exception as e:
                errors[col_name] = f"Error transforming '{col_name}': {e}"

        uploaded_dataframes[df_id]["df"] = current_df
        batch_results[df_id] = {
            "filename": df_info["filename"],
            "successful_reports": successful_reports,
            "errors": errors,
        }

    return render_template("results.html", batch_results=batch_results)


@app.route("/download/<df_id>/<file_format>")
def download_file(df_id, file_format):
    if df_id not in uploaded_dataframes:
        return "Error: DataFrame not found.", 404

    df_info = uploaded_dataframes[df_id]
    if not (isinstance(df_info, dict) and "df" in df_info and "filename" in df_info):
        return "Error: Invalid DataFrame info found.", 400

    df = df_info["df"]
    base_name, _ = os.path.splitext(df_info["filename"])
    download_filename = f"{base_name}_transformed.{file_format}"
    buffer = io.StringIO()

    if file_format == "csv":
        df.to_csv(buffer, index=False)
        mimetype = "text/csv"
    elif file_format == "json":
        df.to_json(buffer, orient="records", indent=4)
        mimetype = "application/json"
    else:
        return "Error: Invalid file format specified.", 400

    buffer.seek(0)
    return send_file(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        mimetype=mimetype,
        as_attachment=True,
        download_name=download_filename,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
